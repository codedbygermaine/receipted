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
    """Whole-unit currencies (rupiah, yen) round to the unit. Cent currencies get 5 cents, because
    several countries (Singapore among them) round cash totals to the nearest 5 cents and print a
    'rounding' line of a cent or two."""
    return TOL_ABS if (currency or "IDR").upper() in NO_CENTS_CURRENCIES else 0.05


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


# Obvious personal-use items (policy C6). A plain word list: transparent, testable, and it holds the claim for a
# person to confirm rather than rejecting, because an event's first-aid kit is a legitimate business purchase.
PERSONAL_ITEM_WORDS = (
    "tablet", "tablets", "capsule", "capsules", "caps", "syrup", "paracetamol", "panadol", "ibuprofen", "imodium", "actal",
    "antacid", "lozenge", "plaster", "plasters", "bandage", "ointment", "cream", "lotion", "serum", "shampoo", "conditioner",
    "toothpaste", "deodorant", "sanitary", "tampon", "razor", "cosmetic", "lipstick", "mascara", "skincare", "moisturiser",
    "moisturizer", "sunscreen", "eye drops", "contact lens", "vitamin", "supplement", "diapers", "baby wipes", "retainer",
    "consultation", "ultrasound", "x-ray", "dental", "clinic",
)


# Policy C7: a single claim above this needs two approvers, so the checker must hold it rather than approve it.
# Enforced in code because a mandatory control cannot depend on the model noticing it every time (it raised C7
# on 1 of 3 test claims). The rule-check voting uses the same thresholds.
TWO_APPROVER_THRESHOLD = {"IDR": 500_000, "SGD": 500}


def _amt(v, receipt: dict | None = None) -> str:
    """An amount the way a person would read it: the receipt's currency, two decimals for cent currencies."""
    if v is None:
        return "nothing"
    cur = (receipt or {}).get("currency") or ""
    whole = cur in ("IDR", "JPY", "KRW", "VND")
    n = f"{round(v):,}" if whole else f"{v:,.2f}"
    return f"{cur} {n}".strip()


def check_personal_items(receipt: dict) -> list[dict]:
    """Deterministic C6 screen: items whose printed name contains a personal-use word are held for confirmation."""
    issues = []
    for it in receipt["items"]:
        name = (it.get("name") or "").lower()
        hits = [w for w in PERSONAL_ITEM_WORDS if w in name]
        if hits and (it.get("line_total") or 0) > 0:
            issues.append({**issue("possible_personal_item", "medium",
                                   f"'{it['name']}' looks like a personal-use item ({hits[0]}); policy C6 excludes these unless the business purpose is confirmed",
                                   {"matched_word": hits[0], "line_total": it.get("line_total")},
                                   receipt_line=it.get("raw_line")),
                           "clause_id": "C6"})
    return issues


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
            shows = " and ".join(f"a {k} of {_amt(v, receipt)}" for k, v in (("subtotal", sub), ("total", total)) if v is not None)
            issues.append(issue("lines_vs_totals", "medium",
                                f"The items as read add up to {_amt(ls, receipt)}, but the receipt shows {shows}. "
                                f"A line may have been misread, so a person should check the receipt",
                                {"line_sum": ls, "subtotal": sub, "total": total}))

    issues += check_personal_items(receipt)

    # 3. subtotal + tax + service - discount = total (or total = subtotal when tax is included)
    if sub is not None and total is not None:
        expected = sub + (tax or 0) + (svc or 0) - abs(disc or 0)
        if not close(expected, total, tol) and not close(sub, total, tol):
            parts = [f"subtotal {_amt(sub, receipt)}"] + [f"{k} {_amt(v, receipt)}" for k, v in (("tax", tax), ("service", svc)) if v] \
                    + ([f"minus discount {_amt(abs(disc), receipt)}"] if disc else [])
            issues.append(issue("totals_arithmetic", "medium",
                                f"{' plus '.join(parts[:1] + parts[1:]).replace('plus minus', 'minus')} comes to {_amt(expected, receipt)}, "
                                f"but the receipt total shows {_amt(total, receipt)}",
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
            issues.append({**issue("claim_exceeds_receipt", "high",
                                   f"Claimed {_amt(amount, receipt)}, but the receipt total is {_amt(receipt_total, receipt)} "
                                   f"({_amt(amount - receipt_total, receipt)} more)",
                                {"claimed": amount, "receipt_total": receipt_total,
                                 "difference": amount - receipt_total}), "clause_id": "C4"})
        else:
            issues.append(issue("claim_below_receipt", "low",
                                f"Claimed {_amt(amount, receipt)}, less than the receipt total of {_amt(receipt_total, receipt)}",
                                {"claimed": amount, "receipt_total": receipt_total}))

    # C7: above the two-approver threshold the claim is held for a second approver, whatever else is found.
    cur = (receipt.get("currency") or "IDR").upper()
    threshold = TWO_APPROVER_THRESHOLD.get(cur, TWO_APPROVER_THRESHOLD["IDR"])
    if amount is not None and amount > threshold:
        issues.append({**issue("two_approvers_required", "medium",
                               f"{_amt(amount, receipt)} is above the {_amt(threshold, receipt)} two-approver threshold, "
                               f"so a second approver must sign off before payment",
                               {"amount": amount, "threshold": threshold}),
                       "clause_id": "C7"})

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
            if extras > 0:
                why = f" (the receipt's tax and service add {extras}, which does not explain the gap)"
            elif extras < 0:
                why = f" (the receipt's discount of {abs(extras)} does not explain the gap)"
            else:
                why = ""
            issues.append(issue("claim_lines_vs_amount", "medium",
                                f"Claim lines sum to {line_sum_claim} but the claimed amount is {amount}" + why,
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
