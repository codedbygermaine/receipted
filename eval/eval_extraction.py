"""Measure extraction against ground truth: field accuracy and item-level precision/recall/F1,
plus latency and cost per receipt, for one model.

Usage: .venv/bin/python eval/eval_extraction.py --split validation --limit 10 --model claude-haiku-5-5
       .venv/bin/python eval/eval_extraction.py --split test --model claude-opus-5-5 --yes
The test split needs --yes: the script first prints the estimated cost and stops without it.
"""

import argparse
import json
import statistics
from pathlib import Path

from rapidfuzz import fuzz

from receipted import llm
from receipted.extract import ExtractionError, extract
from receipted.maths import close

ROOT = Path(__file__).resolve().parents[1]
NAME_THRESHOLD = 80
# typical tokens per receipt, measured on validation runs; used only for the cost estimate
EST_TOKENS = {"input": 3000, "output": 600}


def same(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return close(a, b)


def match_items(gt_items, ex_items):
    """Greedy one-to-one matching on name. Returns per-gt-item (name_matched, numbers_matched)."""
    used, results = set(), []
    for g in gt_items:
        best, best_score = None, 0
        for j, e in enumerate(ex_items):
            if j in used:
                continue
            s = fuzz.token_set_ratio(g["name"].lower(), e["name"].lower())
            if s > best_score:
                best, best_score = j, s
        if best is None or best_score < NAME_THRESHOLD:
            results.append((False, False))
            continue
        used.add(best)
        e = ex_items[best]
        numbers_ok = same(g["qty"], e["qty"]) and same(g["line_total"], e["line_total"])
        results.append((True, numbers_ok))
    return results


def score_receipt(rec, receipt):
    gt_items = [it for it in rec["items"] if it["name"]]
    ex_items = receipt["items"]
    matches = match_items(gt_items, ex_items)
    name_hits = sum(m[0] for m in matches)
    full_hits = sum(m[1] for m in matches)
    return {
        "n_gt_items": len(gt_items), "n_extracted_items": len(ex_items),
        "name_hits": name_hits, "full_hits": full_hits,
        "total_ok": same(rec["total"], receipt["total"]),
        "subtotal_ok": same(rec["subtotal"], receipt["subtotal"]),
        "tax_ok": same(rec["tax"], receipt["tax"]),
        "readability": receipt["readability"],
    }


def prf(hits, n_extracted, n_gt):
    p = hits / n_extracted if n_extracted else 0.0
    r = hits / n_gt if n_gt else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return round(p, 4), round(r, 4), round(f, 4)


def main(split, model, limit, yes):
    recs = json.load(open(ROOT / "data" / "gt" / f"{split}.json"))
    if limit:
        recs = recs[:limit]
    if split == "test" and not yes:
        inp, out = llm.PRICES_PER_MTOK[model]
        est = len(recs) * (EST_TOKENS["input"] * inp + EST_TOKENS["output"] * out) / 1e6
        print(f"ESTIMATE: {len(recs)} receipts x 1 call each on {model} ≈ ${est:.2f} (less if cached). "
              f"Re-run with --yes to proceed.")
        return

    rows = []
    for rec in recs:
        row = {"id": rec["id"], "model": model}
        try:
            r = extract(ROOT / rec["image_path"], model=model)
            row.update(score_receipt(rec, r.receipt))
            row.update({"latency_s": r.latency_s, "cost_usd": r.cost_usd, "input_tokens": r.input_tokens,
                        "output_tokens": r.output_tokens, "attempts": r.attempts, "error": None})
        except ExtractionError as e:
            row.update({"n_gt_items": len(rec["items"]), "n_extracted_items": 0, "name_hits": 0, "full_hits": 0,
                        "total_ok": False, "subtotal_ok": False, "tax_ok": False, "readability": None,
                        "latency_s": None, "cost_usd": 0, "input_tokens": 0, "output_tokens": 0,
                        "attempts": 2, "error": str(e)})
        rows.append(row)
        print(f"  {row['id']}: items {row['full_hits']}/{row['n_gt_items']} exact, total {'ok' if row['total_ok'] else 'X'}, "
              f"{row['latency_s']}s, ${row['cost_usd']:.4f}, {row['readability']}{'  ERROR ' + row['error'] if row['error'] else ''}")

    n = len(rows)
    n_gt = sum(r["n_gt_items"] for r in rows)
    n_ex = sum(r["n_extracted_items"] for r in rows)
    p, rc, f = prf(sum(r["full_hits"] for r in rows), n_ex, n_gt)
    pn, rn, fn = prf(sum(r["name_hits"] for r in rows), n_ex, n_gt)
    latencies = [r["latency_s"] for r in rows if r["latency_s"] is not None]
    summary = {
        "split": split, "model": model, "n_receipts": n,
        "total_accuracy": round(sum(r["total_ok"] for r in rows) / n, 4),
        "subtotal_accuracy": round(sum(r["subtotal_ok"] for r in rows) / n, 4),
        "tax_accuracy": round(sum(r["tax_ok"] for r in rows) / n, 4),
        "item_precision": p, "item_recall": rc, "item_f1": f,
        "item_name_only_precision": pn, "item_name_only_recall": rn, "item_name_only_f1": fn,
        "n_gt_items": n_gt, "n_extracted_items": n_ex,
        "mean_latency_s": round(statistics.mean(latencies), 2) if latencies else None,
        "median_latency_s": round(statistics.median(latencies), 2) if latencies else None,
        "mean_cost_usd": round(sum(r["cost_usd"] for r in rows) / n, 5),
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 4),
        "extraction_errors": sum(1 for r in rows if r["error"]),
        "retries": sum(1 for r in rows if r["attempts"] > 1),
        "readability_counts": {k: sum(1 for r in rows if r["readability"] == k) for k in ("clear", "partly unclear", "unreadable")},
    }
    out = ROOT / "results" / f"extraction_{split}_{model}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "receipts": rows}, indent=1))
    print("\nSUMMARY")
    for k, v in summary.items():
        print(f"  {k:<28} {v}")
    print(f"written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation", choices=["validation", "test"])
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    main(a.split, a.model, a.limit, a.yes)
