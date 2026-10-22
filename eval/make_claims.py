"""Build SYNTHETIC claims for a split from the ground truth, with planted errors and labels.

Half the claims are clean. Each of the rest gets exactly one planted error, spread evenly over:
  inflated_amount      claim amount above the receipt total (one claim line raised to match)
  wrong_quantity       one item claimed with more units than the receipt shows
  item_not_on_receipt  an extra item (a real train-split item name) added to the claim
  totals_mismatch      one claim line changed so the lines no longer sum to the claimed amount
  policy_breach        the claim text breaks a clause: a meal for 1 person over the per-person cap (C12),
                       or no purpose stated (C1)

Two breaches are properties of the receipt, not the claim, so they cannot be planted. They are
labelled from ground truth wherever they occur naturally and feed the expected decision:
  price_above_list     a receipt item is on the price list and priced above the agreed maximum
  alcohol_on_receipt   a receipt item is alcohol or tobacco (C3)
Also labelled: above_500k (C7), packaging_over_5000 (C13), receipt_inconsistent (the ground truth
itself does not add up, so a maths flag is correct, not a false alarm).

Fixed seed, so the file is reproducible. Usage: .venv/bin/python eval/make_claims.py --split test
"""

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz, process

from receipted.maths import close
from receipted.retrieve import load_price_list

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261023
ERROR_TYPES = ["inflated_amount", "wrong_quantity", "item_not_on_receipt", "totals_mismatch", "policy_breach"]
ALCOHOL = re.compile(r"\b(bir|beer|bintang|heineken|guinness|anker|wine|anggur|soju|sake|vodka|whisky|whiskey|"
                     r"cocktail|rokok|cigarette|sampoerna|marlboro|gudang garam)\b", re.I)
PACKAGING = re.compile(r"plastic|plastik|kantong|bag|packaging|kemasan|takeaway|take away", re.I)
PURPOSES = ["Team lunch", "Committee dinner", "Snacks for event booth", "Refreshments for meeting",
            "Supplies for workshop", "Welfare pack items", "Food for volunteers"]
MEAL_WORDS = ("lunch", "dinner", "food", "refreshments", "snacks")

SEVERITY = {  # what a correct checker should conclude for each label
    "inflated_amount": "high", "wrong_quantity": "high", "item_not_on_receipt": "high",
    "totals_mismatch": "medium", "policy_breach": "medium",
    "price_above_list": "medium", "alcohol_on_receipt": "high", "above_500k": "medium",
    "packaging_over_5000": "medium", "receipt_inconsistent": "medium",
}


def unit_price(it):
    if it.get("unit_price"):
        return it["unit_price"]
    if it.get("line_total") is not None and it.get("qty"):
        return it["line_total"] / it["qty"]
    return it.get("line_total")


def natural_flags(rec, price_list):
    flags = []
    names = list(price_list)
    for it in rec["items"]:
        m = process.extractOne(it["name"].lower(), names, scorer=fuzz.ratio)
        u = unit_price(it)
        if m and m[1] >= 90 and u and u > price_list[m[0]]["agreed_max_unit_price"]:
            flags.append("price_above_list")
        if ALCOHOL.search(it["name"]):
            flags.append("alcohol_on_receipt")
    if (rec.get("total") or 0) > 500_000:
        flags.append("above_500k")
    packaging = sum(it["line_total"] or 0 for it in rec["items"] if PACKAGING.search(it["name"]))
    if packaging > 5000:
        flags.append("packaging_over_5000")
    c = rec["checks"]
    if c["lines_match_subtotal"] is False and c["lines_match_total"] is not True:
        flags.append("receipt_inconsistent")
    elif c["subtotal_tax_service_match_total"] is False and not close(rec["subtotal"] or 0, rec["total"] or -1):
        flags.append("receipt_inconsistent")
    return sorted(set(flags))


def base_claim(rec, idx, rng, split):
    amount = rec["total"]
    if amount is None:
        amount = sum(it["line_total"] or 0 for it in rec["items"])
    items = [{"name": it["name"], "qty": it["qty"] if it["qty"] is not None else 1, "line_total": it["line_total"]}
             for it in rec["items"] if it["line_total"] is not None and it["name"]]
    purpose = rng.choice(PURPOSES)
    if any(w in purpose.lower() for w in MEAL_WORDS):
        purpose += f", {rng.randint(2, 6)} people"
    return {
        "claim_id": f"{split.upper()[:3]}-{idx:03d}",
        "receipt_id": rec["id"],
        "image_path": rec["image_path"],
        "submitter": f"Member {idx:03d}",
        "purpose": purpose,
        "amount": int(amount),
        "currency": "IDR",
        "items": items,
    }


def plant(claim, error, rng, train_names):
    """Mutate the claim in place. Returns a dict describing what was planted."""
    items = claim["items"]
    if error == "inflated_amount":
        delta = max(5000, int(round(claim["amount"] * rng.uniform(0.10, 0.40), -3)))
        claim["amount"] += delta
        if items:
            k = rng.randrange(len(items))
            items[k]["line_total"] += delta
        return {"delta": delta}
    if error == "wrong_quantity":
        candidates = [i for i, it in enumerate(items) if it["qty"] and it["line_total"]]
        if not candidates:
            return None
        k = rng.choice(candidates)
        unit = items[k]["line_total"] / items[k]["qty"]
        extra = rng.choice([1, 1, 2])
        items[k]["qty"] += extra
        items[k]["line_total"] = int(round(items[k]["line_total"] + unit * extra))
        claim["amount"] += int(round(unit * extra))
        return {"item": items[k]["name"], "extra_qty": extra}
    if error == "item_not_on_receipt":
        for _ in range(50):
            name = rng.choice(train_names)
            if not items or max(fuzz.token_set_ratio(name.lower(), it["name"].lower()) for it in items) < 60:
                break
        price = rng.choice([8000, 12000, 15000, 18000, 22000, 25000, 30000, 35000, 45000])
        items.append({"name": name, "qty": 1, "line_total": price})
        claim["amount"] += price
        return {"item": name, "price": price}
    if error == "totals_mismatch":
        if not items:
            return None
        k = rng.randrange(len(items))
        delta = max(2000, int(round(items[k]["line_total"] * rng.uniform(0.2, 0.6), -3)))
        items[k]["line_total"] += delta    # amount left unchanged, so lines no longer sum to it
        return {"item": items[k]["name"], "delta": delta}
    if error == "policy_breach":
        if claim["amount"] > 150_000:
            claim["purpose"] = f"{rng.choice(['Dinner', 'Lunch'])}, 1 person"
            return {"clause": "C12", "detail": "meal above 150,000 per person"}
        claim["purpose"] = ""
        return {"clause": "C1", "detail": "no purpose stated"}
    raise ValueError(error)


def expected_decision(labels):
    sev = [SEVERITY[l] for l in labels]
    if "high" in sev:
        return "reject"
    if "medium" in sev:
        return "needs_review"
    return "approve"


def main(split):
    rng = random.Random(SEED)
    recs = json.load(open(ROOT / "data" / "gt" / f"{split}.json"))
    price_list = load_price_list()
    train_names = [l.split("\t")[0] for l in (ROOT / "data" / "train_item_names.txt").read_text().splitlines()]

    order = list(range(len(recs)))
    rng.shuffle(order)
    n_clean = len(order) // 2
    plan = {i: None for i in order[:n_clean]}
    for j, i in enumerate(order[n_clean:]):
        plan[i] = ERROR_TYPES[j % len(ERROR_TYPES)]

    claims = []
    for idx, rec in enumerate(recs):
        claim = base_claim(rec, idx, rng, split)
        error = plan[idx]
        planted = plant(claim, error, rng, train_names) if error else None
        if error and planted is None:      # could not plant on this receipt (no usable items)
            error = "inflated_amount"
            planted = plant(claim, error, rng, train_names)
        flags = natural_flags(rec, price_list)
        labels = ([error] if error else []) + flags
        claim["labels"] = {
            "planted_error": error,
            "planted_detail": planted,
            "natural_flags": flags,
            "expected_decision": expected_decision(labels),
        }
        claims.append(claim)

    out = ROOT / "data" / "claims" / f"{split}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(claims, indent=1, ensure_ascii=False))

    print(f"Wrote {len(claims)} SYNTHETIC claims to {out.relative_to(ROOT)}")
    print("planted errors:", dict(Counter(c["labels"]["planted_error"] or "clean" for c in claims)))
    print("natural flags: ", dict(Counter(f for c in claims for f in c["labels"]["natural_flags"])))
    print("expected decisions:", dict(Counter(c["labels"]["expected_decision"] for c in claims)))
    clean_and_clear = sum(1 for c in claims if not c["labels"]["planted_error"] and not c["labels"]["natural_flags"])
    print(f"clean claims with no natural flags (the false-alarm denominator): {clean_and_clear}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["validation", "test"])
    main(ap.parse_args().split)
