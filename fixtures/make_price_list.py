"""Build the test price list from item names and prices seen in the CORD *train* split only.

For each frequent item name we take the median observed unit price and set the agreed maximum
a little above it, rounded to a sensible rupiah figure. The validation and test splits are never
read here, so nothing about the eval data leaks into the fixture.

Run:  .venv/bin/python fixtures/make_price_list.py
"""

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from datasets import load_dataset

from receipted.parsing import parse_price, parse_qty

ROOT = Path(__file__).resolve().parents[1]
MIN_OCCURRENCES = 3
MARKUP = 1.10


def as_list(x):
    return [] if x is None else (x if isinstance(x, list) else [x])


def as_text(x):
    return " ".join(str(p).strip() for p in x if p) if isinstance(x, list) else (str(x).strip() if x else "")


def unit_price(it):
    u = parse_price(it.get("unitprice"))
    if u is not None and u > 0:
        return u
    p, q = parse_price(it.get("price")), parse_qty(it.get("cnt"))
    if p is not None and p > 0 and q:
        return p / q
    return p if p and p > 0 else None


def round_up(x):
    step = 500 if x < 50_000 else 1000
    return int(math.ceil(x * MARKUP / step) * step)


if __name__ == "__main__":
    ds = load_dataset("naver-clova-ix/cord-v2")
    prices = defaultdict(list)
    for gt in ds["train"]["ground_truth"]:
        for it in as_list(json.loads(gt)["gt_parse"].get("menu")):
            name, u = as_text(it.get("nm")), unit_price(it)
            if name and u:
                prices[name.lower()].append(u)

    rows = []
    for name, seen in sorted(prices.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(seen) < MIN_OCCURRENCES:
            continue
        median = statistics.median(seen)
        rows.append({"item": name, "agreed_max_unit_price": round_up(median),
                     "typical_price_seen": int(median), "times_seen_in_train": len(seen)})

    out = ROOT / "fixtures" / "price_list.csv"
    with open(out, "w", newline="") as f:
        f.write("# Price list written for testing Receipted. Built from item names and prices in the CORD v2 train split\n")
        f.write("# (CC BY 4.0). agreed_max_unit_price = median observed price x 1.10, rounded up. Currency: IDR.\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out.relative_to(ROOT)}")
    for r in rows[:8]:
        print("  ", r)
