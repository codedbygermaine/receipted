"""The LLM rule check: given the facts (extracted receipt, claim, maths results) and the retrieved
policy clauses and price rows, decide which rules are broken. Every issue must cite a clause or
price row AND the receipt line it applies to, so the verifier can check it.
"""

import json
import time
from typing import Literal

from pydantic import BaseModel, Field

from receipted import llm

PROMPT_VERSION = "v3"
VOTES = 1              # default: one rule-check run
VOTES_HIGH_STAKES = 3  # above the two-approver threshold the judgement step runs 3 times and keeps the majority
HIGH_STAKES = {"IDR": 500_000, "SGD": 500}   # the policy C7 thresholds per currency set


def votes_for(amount, currency: str | None) -> int:
    """Spend the extra model calls only where a wrong answer costs the most. Measured on 100 validation
    claims, voting everywhere changed nothing in aggregate at twice the cost; the gain is on the few
    large claims where a single run's variance matters."""
    threshold = HIGH_STAKES.get((currency or "IDR").upper(), HIGH_STAKES["IDR"])
    return VOTES_HIGH_STAKES if amount is not None and amount >= threshold else VOTES

ANCHORS = ("RECEIPT_TOTAL", "CLAIM_AMOUNT")  # allowed receipt_line values for whole-claim rules


class RuleIssue(BaseModel):
    type: str = Field(description="Short snake_case label, e.g. alcohol_item, price_above_list, needs_two_approvers")
    severity: Literal["low", "medium", "high"]
    clause_id: str | None = Field(description="Policy clause id exactly as given, e.g. C3. null if the issue is only about the price list")
    price_item: str | None = Field(description="Price-list item name exactly as given, or null")
    receipt_line: str = Field(description="The receipt line copied exactly, or RECEIPT_TOTAL / CLAIM_AMOUNT for whole-claim rules")
    explanation: str = Field(description="One or two sentences a treasurer could act on")


class RuleIssues(BaseModel):
    issues: list[RuleIssue]


SYSTEM_PROMPT = """You check expense claims for a club treasurer. You are given facts that code has already established
(the extracted receipt lines, the claim, and arithmetic problems already found) plus the policy clauses and
price-list rows that retrieval judged relevant.

Raise an issue ONLY when a given clause or price row clearly applies to a specific receipt line or to the claim.
- clause_id must be one of the clause ids shown. price_item must be one of the price-list item names shown.
- receipt_line must be copied character for character from the RECEIPT LINES, or be RECEIPT_TOTAL / CLAIM_AMOUNT
  when the rule is about the whole claim (e.g. approval thresholds).
- Prices on the receipt are unit prices only when a unit price column is printed; otherwise compare line_total / qty.
- Do not restate the arithmetic issues already listed; they are recorded. You may add a policy issue that follows from one.
- Also check the claim itself against the clauses: its stated purpose (or lack of one), the number of people for a meal,
  and the claimed amount against any approval threshold. Cite CLAIM_AMOUNT as the line for those.
- severity follows the clause wording: "high" when the clause says the claim or item is rejected or never
  reimbursable; "medium" when it says the claim is held for review or needs approval; "low" for anything softer.
- If nothing applies, return an empty list. Never invent clauses, prices or lines."""


def _format_facts(receipt: dict, claim: dict, maths_issues: list[dict], retrieved: dict) -> str:
    lines = []
    purpose = (claim.get("purpose") or "").strip()
    lines.append(f"CLAIM PURPOSE: {purpose if purpose else '(not stated)'}")
    lines.append("CLAIM:\n" + json.dumps(claim, ensure_ascii=False, indent=1))
    lines.append("RECEIPT LINES (copy raw_line exactly when citing):")
    for it in receipt["items"]:
        lines.append(f'- raw_line: "{it["raw_line"]}" | name: {it["name"]} | qty: {it["qty"]} | '
                     f'unit_price: {it["unit_price"]} | line_total: {it["line_total"]}')
    lines.append(f"RECEIPT TOTALS: subtotal={receipt['subtotal']} tax={receipt['tax']} service={receipt['service']} "
                 f"discount={receipt['discount']} total={receipt['total']} currency={receipt['currency']} "
                 f"readability={receipt['readability']}")
    lines.append("ARITHMETIC ISSUES ALREADY FOUND BY CODE:")
    lines += [f"- {m['type']} ({m['severity']}): {m['message']}" for m in maths_issues] or ["- none"]
    lines.append(f"POLICY CLAUSES (retrieved; amounts in this policy are in {retrieved.get('policy_set', 'IDR')}):")
    lines += [f"- {c['id']}. {c['title']}: {c['text']}" for c in retrieved["clauses"]]
    lines.append(f"PRICE LIST ROWS (retrieved per receipt item; agreed_max_unit_price in {retrieved.get('policy_set', 'IDR')}):")
    for name, rows in retrieved["price_rows"].items():
        lines.append(f"- for receipt item '{name}': " +
                     "; ".join(f"'{r['item']}' max {r['agreed_max_unit_price']}" for r in rows))
    return "\n".join(lines)


def _issue_key(issue: dict) -> tuple:
    """Two runs raised 'the same' issue if they cite the same clause or price row on the same line."""
    line = " ".join((issue.get("receipt_line") or "").lower().split())
    return (issue.get("clause_id") or "", issue.get("price_item") or "", line)


def majority(runs: list[list[dict]]) -> tuple[list[dict], dict]:
    """Keep issues raised in at least half of the runs (rounded up). Returns (issues, vote counts)."""
    needed = (len(runs) + 1) // 2
    counts: dict[tuple, int] = {}
    first: dict[tuple, dict] = {}
    for run in runs:
        seen = set()
        for issue in run:
            k = _issue_key(issue)
            if k in seen:
                continue
            seen.add(k)
            counts[k] = counts.get(k, 0) + 1
            first.setdefault(k, issue)
    kept = [{**first[k], "evidence": {**first[k].get("evidence", {}), "votes": f"{c}/{len(runs)}"}}
            for k, c in counts.items() if c >= needed]
    return kept, {"raised_in_any_run": len(counts), "kept_by_majority": len(kept)}


def check_rules(receipt: dict, claim: dict, maths_issues: list[dict], retrieved: dict,
                model: str = llm.DEFAULT_MODEL, votes: int = VOTES) -> tuple[list[dict], dict]:
    """Returns (issues, meta). With votes > 1 the model is asked `votes` times and only issues that a majority
    of runs agree on are raised; meta sums tokens and cost across the runs."""
    facts = _format_facts(receipt, claim, maths_issues, retrieved)
    if votes > 1:
        runs, metas = [], []
        for v in range(votes):
            issues, meta = _single_run(facts, model, vote=v)
            runs.append(issues); metas.append(meta)
        kept, tally = majority(runs)
        meta = {"model": model, "votes": votes, **tally,
                "input_tokens": sum(m["input_tokens"] for m in metas), "output_tokens": sum(m["output_tokens"] for m in metas),
                "latency_s": round(sum(m["latency_s"] for m in metas), 2), "cost_usd": round(sum(m["cost_usd"] for m in metas), 6),
                "cached": all(m["cached"] for m in metas)}
        return kept, meta
    return _single_run(facts, model, vote=0)


def _single_run(facts: str, model: str, vote: int) -> tuple[list[dict], dict]:
    key = llm.cache_key(facts, PROMPT_VERSION, model, SYSTEM_PROMPT, f"vote{vote}")
    hit = llm.cache_get("rules", key)
    if hit:
        return hit["issues"], {**hit["meta"], "cached": True}

    start = time.perf_counter()
    response = llm.client().messages.parse(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": facts}],
        output_format=RuleIssues,
        output_config={"effort": "medium"},
    )
    parsed = response.parsed_output
    raw = parsed.issues if parsed is not None else []
    issues = [{
        "source": "rules",
        "type": r.type,
        "severity": r.severity,
        "message": r.explanation,
        "receipt_line": r.receipt_line,
        "clause_id": r.clause_id,
        "price_item": r.price_item,
        "evidence": {},
    } for r in raw]
    meta = {
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_s": round(time.perf_counter() - start, 2),
        "cost_usd": round(llm.cost_usd(model, response.usage.input_tokens, response.usage.output_tokens), 6),
        "stop_reason": response.stop_reason,
        "cached": False,
    }
    llm.cache_put("rules", key, {"issues": issues, "meta": meta})
    return issues, meta
