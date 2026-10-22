"""The evidence verifier. Plain Python, no LLM.

An issue from the rule check survives only if its citations are real:
  - the clause id exists in policy.md, or the price item exists in price_list.csv, and
  - the receipt line it cites is one of the extracted lines (after whitespace normalisation),
    or one of the two whole-claim anchors.
For price-list issues we also re-do the comparison in code: the cited line's unit price must
really be above the agreed maximum. Maths issues pass through: their evidence was computed by code.
"""

import re

from rapidfuzz import fuzz

ANCHORS = {"RECEIPT_TOTAL", "CLAIM_AMOUNT"}
LINE_MATCH_THRESHOLD = 95


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def find_line(receipt_line: str, receipt: dict):
    """Return the extracted item whose raw_line matches, or None."""
    target = _norm(receipt_line)
    for it in receipt["items"]:
        if _norm(it["raw_line"]) == target:
            return it
    for it in receipt["items"]:  # tolerate a stray character
        if fuzz.ratio(_norm(it["raw_line"]), target) >= LINE_MATCH_THRESHOLD:
            return it
    return None


def unit_price_of(item: dict):
    if item.get("unit_price") is not None:
        return item["unit_price"]
    if item.get("line_total") is not None and item.get("qty"):
        return item["line_total"] / item["qty"]
    return item.get("line_total")


def verify(issues: list[dict], receipt: dict, clauses: dict, price_list: dict) -> tuple[list[dict], list[dict]]:
    """Returns (kept, dropped). Dropped issues carry a 'dropped_because' reason."""
    kept, dropped = [], []
    for issue in issues:
        if issue["source"] != "rules":
            kept.append(issue)
            continue

        clause = clauses.get(issue.get("clause_id") or "")
        price_row = price_list.get(issue.get("price_item") or "")
        if clause is None and price_row is None:
            dropped.append({**issue, "dropped_because": "cited clause/price item does not exist"})
            continue

        line = issue.get("receipt_line") or ""
        item = None
        if line not in ANCHORS:
            item = find_line(line, receipt)
            if item is None:
                dropped.append({**issue, "dropped_because": "cited receipt line is not in the extraction"})
                continue

        evidence = dict(issue.get("evidence") or {})
        if clause is not None:
            evidence["clause_text"] = f"{clause['id']}. {clause['title']}: {clause['text']}"
        if price_row is not None:
            paid = unit_price_of(item) if item is not None else None
            if paid is None or paid <= price_row["agreed_max_unit_price"]:
                dropped.append({**issue, "dropped_because":
                                f"unit price {paid} is not above the agreed max {price_row['agreed_max_unit_price']}"})
                continue
            evidence.update({"unit_price_paid": paid, "agreed_max_unit_price": price_row["agreed_max_unit_price"],
                             "price_list_item": price_row["item"]})
        kept.append({**issue, "evidence": evidence})
    return kept, dropped
