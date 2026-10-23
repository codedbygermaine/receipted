"""Audit log: one JSON line per decision, so any payment can be explained after the fact.

Finance systems live on this. Each record carries what was claimed, what was decided, every issue with
its evidence, which model and prompt versions produced it, what it cost, and what a reviewer did.
Reviewer decisions are also exported as correction records that later evaluations can replay.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from receipted import draft, extract, llm, rules

AUDIT_PATH = llm.ROOT / "data" / "audit_log.jsonl"
CORRECTIONS_PATH = llm.ROOT / "data" / "review_corrections.json"
AUDIT_SAMPLE_RATE = 10   # 1 in N auto-approved claims is marked for a random human audit


def is_audit_sample(fingerprint: str | None, decision: str | None, rate: int = AUDIT_SAMPLE_RATE) -> bool:
    """Deterministic 1-in-N pick of auto-approved claims, keyed on the image fingerprint so the same
    receipt gets the same answer. Pros audit a random slice of what was approved; it is how systematic
    errors in the 'approve' bucket get found."""
    if decision != "approve" or not fingerprint:
        return False
    return int(fingerprint, 16) % rate == 0


def record(state: dict, source: str, reviewer_note: str | None = None) -> dict:
    """Append one decision to the audit log. source: cli | app | mcp | review."""
    receipt = state.get("receipt") or {}
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "claim_id": state["claim"].get("claim_id"),
        "submitter": state["claim"].get("submitter"),
        "claimed_amount": state["claim"].get("amount"),
        "currency": receipt.get("currency") or state["claim"].get("currency"),
        "receipt_total": receipt.get("total"),
        "image_fingerprint": state.get("fingerprint"),
        "decision": state.get("decision"),
        "decision_reason": state.get("decision_reason"),
        "reviewed_by_human": bool(state.get("reviewed_by_human")),
        "audit_sample": (not state.get("reviewed_by_human")) and is_audit_sample(state.get("fingerprint"), state.get("decision")),
        "reviewer_note": reviewer_note,
        "issues": [{k: i.get(k) for k in ("source", "type", "severity", "clause_id", "price_item", "receipt_line", "message")}
                   for i in state.get("verified_issues", [])],
        "dropped_by_verifier": len(state.get("dropped_issues", [])),
        "versions": {"model": state.get("model"), "extract_prompt": extract.PROMPT_VERSION,
                     "rules_prompt": rules.PROMPT_VERSION, "draft_prompt": draft.PROMPT_VERSION},
        "cost_usd": state.get("total_cost_usd"),
        "seconds": state.get("total_seconds"),
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if entry["reviewed_by_human"]:
        _add_correction(entry)
    return entry


def _add_correction(entry: dict) -> None:
    """Reviewer outcomes become labelled cases: the agent's own decision is in the audit log just before."""
    corrections = json.loads(CORRECTIONS_PATH.read_text()) if CORRECTIONS_PATH.exists() else []
    corrections = [c for c in corrections if c["claim_id"] != entry["claim_id"]]
    corrections.append({"claim_id": entry["claim_id"], "image_fingerprint": entry["image_fingerprint"],
                        "human_decision": entry["decision"], "reviewer_note": entry["reviewer_note"], "at": entry["at"],
                        "issues_shown": [i["type"] for i in entry["issues"]]})
    CORRECTIONS_PATH.write_text(json.dumps(corrections, indent=1, ensure_ascii=False))


def audit_samples() -> list[dict]:
    """Approved claims picked for a random audit that nobody has looked at yet."""
    seen_reviewed = {e["claim_id"] for e in recent(100000) if e.get("reviewed_by_human")}
    return [e for e in recent(100000) if e.get("audit_sample") and e["claim_id"] not in seen_reviewed]


def recent(n: int = 50) -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    lines = AUDIT_PATH.read_text().splitlines()
    return [json.loads(l) for l in lines[-n:]][::-1]
