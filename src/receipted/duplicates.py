"""Duplicate-receipt detection (policy C9: the same receipt may not be claimed twice). Plain Python.

A small JSON registry remembers every claim that was approved or held for review: the image's
fingerprint, the receipt total and its item names. A new claim is a duplicate if the fingerprint is
identical (same photo again) or, with a different photo, the total matches and most item names match.
Rejected claims are not registered, so a corrected resubmission is not flagged.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from rapidfuzz import fuzz

from receipted.llm import ROOT

REGISTRY_PATH = ROOT / "data" / "claims_registry.json"
NAME_OVERLAP_THRESHOLD = 0.8   # share of item names that must match for a "likely duplicate"


def image_fingerprint(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()[:16]


def _names(receipt: dict) -> list[str]:
    return [it["name"].lower().strip() for it in receipt["items"] if it.get("name")]


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def find_duplicate(fingerprint: str, receipt: dict, claim_id: str | None = None,
                   path: Path = REGISTRY_PATH) -> dict | None:
    """Return the matching registry entry (with a 'reason'), or None."""
    names = _names(receipt)
    for entry in _load(path):
        if claim_id and entry["claim_id"] == claim_id:
            continue  # the same claim re-run is not a duplicate of itself
        if entry["fingerprint"] == fingerprint:
            return {**entry, "reason": "same receipt image already claimed"}
        if receipt.get("total") is not None and entry["total"] == receipt["total"] and names and entry["item_names"]:
            matched = sum(1 for n in names if max((fuzz.ratio(n, m) for m in entry["item_names"]), default=0) >= 85)
            overlap = matched / max(len(names), len(entry["item_names"]))
            if overlap >= NAME_OVERLAP_THRESHOLD:
                return {**entry, "reason": f"same total and {overlap:.0%} of item names already claimed"}
    return None


def register(claim_id: str, fingerprint: str, receipt: dict, decision: str, path: Path = REGISTRY_PATH) -> None:
    """Remember a claim so later submissions of the same receipt are caught. Rejected claims are skipped."""
    if decision == "reject":
        return
    entries = [e for e in _load(path) if e["claim_id"] != claim_id]
    entries.append({"claim_id": claim_id, "fingerprint": fingerprint, "total": receipt.get("total"),
                    "item_names": _names(receipt), "decision": decision,
                    "registered_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=1, ensure_ascii=False))


def duplicate_issue(match: dict) -> dict:
    return {
        "source": "maths", "type": "duplicate_receipt", "severity": "high",
        "message": f"This receipt was already claimed as {match['claim_id']} ({match['reason']}); policy C9 forbids claiming it twice",
        "receipt_line": "RECEIPT_TOTAL", "clause_id": "C9", "price_item": None,
        "evidence": {"previous_claim_id": match["claim_id"], "previous_decision": match["decision"],
                     "registered_at": match["registered_at"], "reason": match["reason"]},
    }
