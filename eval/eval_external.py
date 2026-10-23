"""Evaluate extraction on an external receipt set with hand-written labels (a format the system
was never tuned on). Labels: data/external/<set>/labels.json, a list of
  {"file": ..., "currency": "GBP", "items": [{"name", "qty", "line_total"}], "subtotal", "tax", "service",
   "discount", "total", "notes"}
Prices in the currency's major unit with decimals (12.99), unlike CORD's whole rupiah.

Usage: .venv/bin/python eval/eval_external.py --set commons --model claude-haiku-5-5
"""

import argparse
import json
import statistics
from pathlib import Path

from receipted import llm, maths
from receipted.extract import ExtractionError, extract
from receipted.maths import tolerance_for

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_extraction import prf  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402


def same(a, b, tol):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= tol


def match_items(gt_items, ex_items, tol):
    """One-to-one by name; numbers must agree to the currency's tolerance. A quantity the receipt
    does not print comes back as null from the model; that counts as 1 when the label says 1."""
    used, out = set(), []
    for g in gt_items:
        best, score = None, 0
        for j, e in enumerate(ex_items):
            if j in used:
                continue
            s_ = fuzz.token_set_ratio(g["name"].lower(), e["name"].lower())
            if s_ > score:
                best, score = j, s_
        if best is None or score < 80:
            out.append((False, False)); continue
        used.add(best); e = ex_items[best]
        qty_e = 1 if (e["qty"] is None and g["qty"] == 1) else e["qty"]
        out.append((True, same(g["qty"], qty_e, 0.001) and same(g["line_total"], e["line_total"], tol)))
    return out


def main(set_name, model):
    base = ROOT / "data" / "external" / set_name
    labels = json.load(open(base / "labels.json"))
    rows = []
    for lab in labels:
        path = base / lab["file"]
        row = {"file": lab["file"], "currency_expected": lab["currency"]}
        try:
            r = extract(path, model=model)
            e = r.receipt
            tol = tolerance_for(lab["currency"])
            matches = match_items(lab["items"], e["items"], tol)
            row.update({
                "currency_got": e["currency"], "currency_ok": e["currency"].upper() == lab["currency"].upper(),
                "total_ok": same(lab["total"], e["total"], tol), "subtotal_ok": same(lab.get("subtotal"), e["subtotal"], tol),
                "tax_ok": same(lab.get("tax"), e["tax"], tol),
                "n_gt_items": len(lab["items"]), "n_extracted_items": len(e["items"]),
                "name_hits": sum(m[0] for m in matches), "full_hits": sum(m[1] for m in matches),
                "readability": e["readability"], "receipt_maths_issues": [i["type"] for i in maths.check_receipt(e)],
                "latency_s": r.latency_s, "cost_usd": r.cost_usd, "extracted_total": e["total"], "label_total": lab["total"],
            })
        except ExtractionError as ex:
            row.update({"error": str(ex), "total_ok": False, "currency_ok": False, "n_gt_items": len(lab["items"]),
                        "n_extracted_items": 0, "name_hits": 0, "full_hits": 0, "cost_usd": 0, "latency_s": None})
        rows.append(row)
        print(f"  {lab['file'][:45]:<45} {row.get('currency_got', '?'):<4} total {'ok' if row['total_ok'] else 'X'} "
              f"({row.get('extracted_total')} vs {lab['total']})  items {row['full_hits']}/{row['n_gt_items']} exact, "
              f"{row['name_hits']} by name  {row.get('readability', '')}  maths={row.get('receipt_maths_issues', [])}")
    n = len(rows)
    n_gt = sum(r["n_gt_items"] for r in rows); n_ex = sum(r["n_extracted_items"] for r in rows)
    p, rc, f = prf(sum(r["full_hits"] for r in rows), n_ex, n_gt)
    pn, rn, fn = prf(sum(r["name_hits"] for r in rows), n_ex, n_gt)
    summary = {"set": set_name, "model": model, "n_receipts": n,
               "currency_accuracy": round(sum(bool(r.get("currency_ok")) for r in rows) / n, 3),
               "total_accuracy": round(sum(bool(r["total_ok"]) for r in rows) / n, 3),
               "item_f1": f, "item_precision": p, "item_recall": rc, "item_name_only_f1": fn,
               "n_gt_items": n_gt, "n_extracted_items": n_ex,
               "receipts_with_maths_issues": sum(1 for r in rows if r.get("receipt_maths_issues")),
               "mean_latency_s": round(statistics.mean([r["latency_s"] for r in rows if r["latency_s"]]), 2),
               "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 4),
               "readability_counts": {k: sum(1 for r in rows if r.get("readability") == k) for k in ("clear", "partly unclear", "unreadable")}}
    out = ROOT / "results" / f"external_{set_name}_{model}.json"
    out.write_text(json.dumps({"summary": summary, "receipts": rows}, indent=1))
    print("\nSUMMARY", json.dumps(summary, indent=1)); print("written to", out.relative_to(ROOT))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="commons")
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    a = ap.parse_args()
    main(a.set, a.model)
