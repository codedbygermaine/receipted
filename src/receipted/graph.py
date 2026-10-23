"""The agent graph. Each node is a plain function over a shared state dict; LangGraph wires them up
and handles the one branch we need: unreadable receipts skip the checks and go to a human.

    extract -> maths_check -> retrieve -> rule_check -> verify -> decide -> draft
       \\___________________ (unreadable / failed) ___________________/^
"""

import operator
import time
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from receipted import llm, maths
from receipted.draft import write_draft
from receipted.duplicates import duplicate_issue, find_duplicate, image_fingerprint, register
from receipted.extract import ExtractionError, extract, prepare_image
from receipted.retrieve import load_policy_clauses, load_price_list, retrieve_for
from receipted.rules import check_rules
from receipted.verify import verify


class State(TypedDict, total=False):
    image_path: str
    claim: dict
    model: str
    register: bool            # remember this claim for duplicate detection (CLI/app/MCP yes, eval runs no)
    fingerprint: str
    receipt: dict | None
    extraction_meta: dict
    error: str | None
    maths_issues: list
    retrieved: dict
    rule_issues: list
    rule_meta: dict
    verified_issues: list
    dropped_issues: list
    decision: str
    decision_reason: str
    draft: str
    draft_meta: dict
    trace: Annotated[list, operator.add]   # every node appends its own entry


def traced(name):
    """Wrap a node so the trace records how long it took and a one-line summary of its output."""
    def deco(fn):
        def wrapped(state):
            t0 = time.perf_counter()
            out = fn(state)
            summary = out.pop("_summary", "")
            entry = {"node": name, "seconds": round(time.perf_counter() - t0, 3), "summary": summary}
            for meta_key in ("extraction_meta", "rule_meta", "draft_meta"):
                if meta_key in out:
                    m = out[meta_key]
                    entry.update({k: m.get(k) for k in ("model", "input_tokens", "output_tokens", "cost_usd", "cached")})
            return {**out, "trace": [entry]}
        wrapped.__name__ = name
        return wrapped
    return deco


@traced("extract")
def node_extract(state):
    try:
        r = extract(state["image_path"], model=state["model"])
    except ExtractionError as e:
        return {"receipt": None, "error": str(e), "extraction_meta": {},
                "_summary": f"extraction failed: {e}"}
    meta = {k: getattr(r, k) for k in ("model", "input_tokens", "output_tokens", "latency_s", "cost_usd", "attempts", "cached")}
    fingerprint = image_fingerprint(prepare_image(state["image_path"])[0])
    return {"receipt": r.receipt, "error": None, "extraction_meta": meta, "fingerprint": fingerprint,
            "_summary": f"{len(r.receipt['items'])} items, total={r.receipt['total']}, readability={r.receipt['readability']}"}


def route_after_extract(state) -> str:
    if state.get("error") or state["receipt"]["readability"] == "unreadable":
        return "decide"
    return "maths_check"


@traced("maths_check")
def node_maths(state):
    issues = maths.check_receipt(state["receipt"]) + maths.check_claim(state["claim"], state["receipt"])
    match = find_duplicate(state["fingerprint"], state["receipt"], claim_id=state["claim"].get("claim_id"))
    if match:
        issues.append(duplicate_issue(match))
    return {"maths_issues": issues, "_summary": f"{len(issues)} issues: {[i['type'] for i in issues]}"}


@traced("retrieve")
def node_retrieve(state):
    retrieved = retrieve_for(state["receipt"], state["claim"])
    return {"retrieved": retrieved,
            "_summary": f"{len(retrieved['clauses'])} clauses {[c['id'] for c in retrieved['clauses']]}, "
                        f"price rows for {len(retrieved['price_rows'])} items"}


@traced("rule_check")
def node_rules(state):
    issues, meta = check_rules(state["receipt"], state["claim"], state["maths_issues"], state["retrieved"],
                               model=state["model"])
    return {"rule_issues": issues, "rule_meta": meta,
            "_summary": f"{len(issues)} issues: {[(i['type'], i['clause_id'] or i['price_item']) for i in issues]}"}


@traced("verify")
def node_verify(state):
    kept, dropped = verify(state["maths_issues"] + state["rule_issues"], state["receipt"],
                           load_policy_clauses(), load_price_list())
    return {"verified_issues": kept, "dropped_issues": dropped,
            "_summary": f"kept {len(kept)}, dropped {len(dropped)}" +
                        (f" ({[d['dropped_because'] for d in dropped]})" if dropped else "")}


def low_confidence_lines(receipt) -> list[str]:
    """Which lines that matter were read with low confidence? (Older cached extractions have no confidence
    fields; they are treated as high so behaviour is unchanged for them.)"""
    lows = [it["raw_line"] for it in receipt["items"] if it.get("confidence") == "low"]
    if receipt.get("total_confidence") == "low":
        lows.append("TOTAL")
    return lows


def decide(receipt, error, issues) -> tuple[str, str]:
    """The decision rule, kept separate so it is easy to read and test."""
    if error:
        return "needs_review", f"could not extract the receipt: {error}"
    if receipt["readability"] == "unreadable":
        return "needs_review", "the receipt is unreadable (policy C10)"
    severities = {i["severity"] for i in issues}
    if "high" in severities:
        return "reject", "at least one high-severity issue with evidence"
    if "medium" in severities:
        return "needs_review", "medium-severity issues need a human decision"
    lows = low_confidence_lines(receipt)
    if lows:
        return "needs_review", f"no issues found, but these lines were read with low confidence: {lows}"
    if receipt["readability"] == "partly unclear":
        return "approve", "no issues found; parts of the receipt were hard to read but every item and the total were legible"
    return "approve", "no issues found and the receipt is clear"


@traced("decide")
def node_decide(state):
    decision, reason = decide(state.get("receipt"), state.get("error"), state.get("verified_issues", []))
    if state.get("register") and state.get("receipt") and state.get("fingerprint"):
        register(state["claim"].get("claim_id") or "unknown", state["fingerprint"], state["receipt"], decision)
    return {"decision": decision, "decision_reason": reason, "_summary": f"{decision}: {reason}"}


@traced("draft")
def node_draft(state):
    text, meta = write_draft(state["claim"], state.get("receipt"), state["decision"], state["decision_reason"],
                             state.get("verified_issues", []), model=state["model"])
    return {"draft": text, "draft_meta": meta, "_summary": f"{len(text.split())} words"}


def build_graph():
    g = StateGraph(State)
    g.add_node("extract", node_extract)
    g.add_node("maths_check", node_maths)
    g.add_node("retrieve", node_retrieve)
    g.add_node("rule_check", node_rules)
    g.add_node("verify", node_verify)
    g.add_node("decide", node_decide)
    g.add_node("draft", node_draft)

    g.add_edge(START, "extract")
    g.add_conditional_edges("extract", route_after_extract, {"maths_check": "maths_check", "decide": "decide"})
    g.add_edge("maths_check", "retrieve")
    g.add_edge("retrieve", "rule_check")
    g.add_edge("rule_check", "verify")
    g.add_edge("verify", "decide")
    g.add_edge("decide", "draft")
    g.add_edge("draft", END)
    return g.compile()


_graph = None


def run_claim(image_path: str, claim: dict, model: str = llm.DEFAULT_MODEL, register: bool = False) -> dict:
    """Run one receipt + claim through the graph. Returns the final state, with totals added.
    register=True records the claim for duplicate detection; eval runs leave it False."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    t0 = time.perf_counter()
    state = _graph.invoke({"image_path": str(image_path), "claim": claim, "model": model, "register": register,
                           "fingerprint": "", "trace": []})
    state["total_seconds"] = round(time.perf_counter() - t0, 2)
    state["total_cost_usd"] = round(sum(e.get("cost_usd") or 0 for e in state["trace"]), 6)
    state.setdefault("verified_issues", [])
    state.setdefault("dropped_issues", [])
    return state
