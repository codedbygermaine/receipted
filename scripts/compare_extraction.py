"""Run extraction on a few validation receipts and print extracted vs ground truth side by side.

Usage: .venv/bin/python scripts/compare_extraction.py [n_receipts] [model]
"""

import json
import sys
from pathlib import Path

from receipted import llm
from receipted.extract import extract

ROOT = Path(__file__).resolve().parents[1]
n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
model = sys.argv[2] if len(sys.argv) > 2 else llm.DEFAULT_MODEL

gt = json.load(open(ROOT / "data" / "gt" / "validation.json"))[:n]


def num(x):
    if x is None:
        return "-"
    return str(int(x)) if float(x).is_integer() else str(x)


total_cost = 0.0
for rec in gt:
    r = extract(ROOT / rec["image_path"], model=model)
    e = r["receipt"] if isinstance(r, dict) else r.receipt
    total_cost += r.cost_usd
    print(f"\n==== {rec['id']}  [{r.model}, {r.latency_s}s, {r.input_tokens} in / {r.output_tokens} out, "
          f"${r.cost_usd:.4f}, attempts={r.attempts}, cached={r.cached}]  readability={e['readability']}")
    width = max(len(it["name"]) for it in rec["items"] + e["items"]) + 2
    print(f"  {'GROUND TRUTH':<{width + 20}}| EXTRACTED")
    rows = max(len(rec["items"]), len(e["items"]))
    for i in range(rows):
        g = rec["items"][i] if i < len(rec["items"]) else None
        x = e["items"][i] if i < len(e["items"]) else None
        gs = f"{num(g['qty']):>3} {g['name']:<{width}}{num(g['unit_price']):>7} {num(g['line_total']):>8}" if g else ""
        xs = f"{num(x['qty']):>3} {x['name']:<{width}}{num(x['unit_price']):>7} {num(x['line_total']):>8}" if x else ""
        print(f"  {gs:<{width + 20}}| {xs}")
    for f in ("subtotal", "tax", "service", "discount", "total"):
        mark = "OK" if (rec[f] is None and e[f] is None) or (rec[f] is not None and e[f] is not None and abs(rec[f] - e[f]) < 1) else "DIFF"
        print(f"  {f:<10} gt={num(rec[f]):>8}  extracted={num(e[f]):>8}  {mark}")
print(f"\nTotal cost this run: ${total_cost:.4f}")
