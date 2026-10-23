"""Deterministic checks. No LLM here: arithmetic and name matching are things code does exactly.

Every failed check returns an issue dict with the numbers involved as evidence, so a reader can
re-do the sum by hand. The LLM later gets these as facts, not opinions.

Tolerance: real receipts round to the nearest thousand rupiah and print tax to the rupiah, so we
allow max(1 unit, 0.5%) before calling a difference an error.
"""

from rapidfuzz import fuzz

TOL_ABS = 1
TOL_REL = 0.005
NAME_MATCH_THRESHOLD = 70  # rapidfuzz token_set_ratio, 0-100
NO_CENTS_CURRENCIES = {"IDR", "JPY", "KRW", "VND", "HUF", "CLP", "ISK", "TWD"}


def tolerance_for(currency: str | None) -> float:
    """Whole-unit currencies (rupiah, yen) round to the unit; everything else prints cents."""
    return TOL_ABS if (currency or "IDR").upper() in NO_CENTS_CURRENCIES else 0.01


def close(a, b, tol_abs: float = TOL_ABS) -> bool:
    return abs(a - b) <= max(tol_abs, TOL_REL * max(abs(a), abs(b)))


def issue(type_, severity, message, evidence, receipt_line=None):
    return {
        "source": "maths",
        "type": type_,
        "severity": severity,       # "low" | "medium" | "high"
        "message": message,
        "receipt_line": receipt_line,
        "clause_id": None,
        "price_item": None,
        "evidence": evidence,
    }


def line_sum(receipt: dict):
    """Sum of printed line totals, including per-item discounts if the extraction has them."""
    totals = [it["line_total"] for it in receipt["items"] if it.get("line_total") is not None]
    if not totals:
        return None
    discounts = sum(it.get("discount") or 0 for it in receipt["items"])
    return sum(totals) + discounts  # discounts are stored negative


def check_receipt(receipt: dict) -> list[dict]:
    """Does the receipt agree with itself?"""
    issues = []
    items = receipt["items"]
    tol = tolerance_for(receipt.get("currency"))

    if not items:
        issues.append(issue("no_line_items", "medium",
                            "No line items were found on the receipt", {}))
        return issues

    # 1. qty x unit price = line total, where all three are printed
    for it in items:
        q, u, t = it.get("qty"), it.get("unit_price"), it.get("line_total")
        if q is not None and u is not None and t is not None and not close(q * u, t, tol):
            issues.append(issue("line_arithmetic", "medium",
                                f"{q} x {u} = {q * u}, but the line shows {t}",
                                {"qty": q, "unit_price": u, "expected": q * u, "line_total": t},
                                receipt_line=it.get("raw_line")))

    # 2. line items add up to the subtotal (or to the total, when prices include tax)
    ls = line_sum(receipt)
    sub, tax, svc, disc, total = (receipt.get(k) for k in ("subtotal", "tax", "service", "discount", "total"))
    if ls is not None:
        targets = [v for v in (sub, total) if v is not None]
        if targets and not any(close(ls, v, tol) for v in targets):
            issues.append(issue("lines_vs_totals", "medium",
                                f"Line items sum to {ls}, but subtotal is {sub} and total is {total}",
                                {"line_sum": ls, "subtotal": sub, "total": total}))

    # 3. subtotal + tax + service - discount = total (or total = subtotal when tax is included)
    if sub is not None and total is not None:
        expected = sub + (tax or 0) + (svc or 0) - abs(disc or 0)
        if not close(expected, total, tol) and not close(sub, total, tol):
            issues.append(issue("totals_arithmetic", "medium",
                                f"{sub} + tax {tax or 0} + service {svc or 0} - discount {abs(disc or 0)} = {expected}, "
                                f"but total shows {total}",
                                {"subtotal": sub, "tax": tax, "service": svc, "discount": disc,
                                 "expected": expected, "total": total}))
    return issues


def name_similarity(a: str, b: str) -> float:
    """0-100. Compared on words, and again with all spaces removed, because receipts sometimes print
    names with no spaces at all ("SATECATIGO" for "SATE ATI GO"). The better score wins."""
    a, b = a.lower().strip(), b.lower().strip()
    return max(fuzz.token_set_ratio(a, b), fuzz.ratio(a.replace(" ", ""), b.replace(" ", "")))


def best_match(name: str, items: list[dict]):
    """Closest receipt item by name. Returns (item, score)."""
    best, best_score = None, 0
    for it in items:
        score = name_similarity(name, it["name"])
        if score > best_score:
            best, best_score = it, score
    return best, best_score


def check_claim(claim: dict, receipt: dict) -> list[dict]:
    """Does the claim agree with the receipt?"""
    issues = []
    tol = tolerance_for(receipt.get("currency"))
    receipt_total = receipt.get("total")
    if receipt_total is None:
        receipt_total = line_sum(receipt)

    # 1. claimed amount vs receipt total
    amount = claim.get("amount")
    if amount is not None and receipt_total is not None and not close(amount, receipt_total, tol):
        if amount > receipt_total:
            issues.append(issue("claim_exceeds_receipt", "high",
                                f"Claimed {amount} but the receipt total is {receipt_total}",
                                {"claimed": amount, "receipt_total": receipt_total,
                                 "difference": amount - receipt_total}))
        else:
            issues.append(issue("claim_below_receipt", "low",
                                f"Claimed {amount}, less than the receipt total {receipt_total}",
                                {"claimed": amount, "receipt_total": receipt_total}))

    claim_items = claim.get("items") or []

    # 1b. a purpose must be stated (policy C1). A one-line rule, so code checks it, not the model.
    if not (claim.get("purpose") or "").strip():
        issues.append({**issue("purpose_missing", "medium",
                               "No purpose is stated on the claim; policy C1 requires one",
                               {"purpose": claim.get("purpose")}),
                       "clause_id": "C1", "receipt_line": "CLAIM_AMOUNT"})

    # 2. claim's own lines add up to its amount. Claim forms list items before tax, so lines that
    #    equal the receipt subtotal, or the amount once the receipt's tax and service are added, are fine.
    claimed_lines = [ci.get("line_total") for ci in claim_items if ci.get("line_total") is not None]
    if claimed_lines and amount is not None:
        line_sum_claim = sum(claimed_lines)
        extras = (receipt.get("tax") or 0) + (receipt.get("service") or 0) - abs(receipt.get("discount") or 0)
        acceptable = [amount, amount - extras]
        if receipt.get("subtotal") is not None:
            acceptable.append(receipt["subtotal"])
        if not any(close(line_sum_claim, target, tol) for target in acceptable):
            issues.append(issue("claim_lines_vs_amount", "medium",
                                f"Claim lines sum to {line_sum_claim} but the claimed amount is {amount}"
                                + (f" (receipt tax + service = {extras})" if extras else ""),
                                {"claim_line_sum": line_sum_claim, "claimed": amount, "receipt_tax_and_service": extras}))

    # 3. each claimed item exists on the receipt, with no more quantity than the receipt shows
    for ci in claim_items:
        match, score = best_match(ci["name"], receipt["items"])
        if match is None or score < NAME_MATCH_THRESHOLD:
            issues.append(issue("claimed_item_not_on_receipt", "high",
                                f"'{ci['name']}' is claimed but no receipt line matches it",
                                {"claimed_name": ci["name"], "closest": match["name"] if match else None,
                                 "match_score": score}))
            continue
        cq, rq = ci.get("qty"), match.get("qty")
        if cq is not None and rq is not None and cq > rq:
            issues.append(issue("claimed_qty_exceeds_receipt", "high",
                                f"Claimed {cq} x '{ci['name']}' but the receipt shows {rq}",
                                {"claimed_qty": cq, "receipt_qty": rq, "receipt_item": match["name"]},
                                receipt_line=match.get("raw_line")))
    return issues
