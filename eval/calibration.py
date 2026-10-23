"""Confidence calibration: when the model says an item is 'high' confidence, how often is it right?
Pros measure this on their own documents before trusting a score. Uses the cached extractions of a split.

Usage: .venv/bin/python eval/calibration.py --split validation
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_extraction import NAME_THRESHOLD, same  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402

from receipted import llm  # noqa: E402
from receipted.extract import extract  # noqa: E402
from receipted.maths import close  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(split, model):
    gt = json.load(open(ROOT / "data" / "gt" / f"{split}.json"))
    buckets = {"high": [0, 0], "medium": [0, 0], "low": [0, 0]}      # [items, correct]
    totals = {"high": [0, 0], "medium": [0, 0], "low": [0, 0]}
    for rec in gt:
        e = extract(ROOT / rec["image_path"], model=model).receipt
        # total
        tc = e.get("total_confidence")
        if tc in totals:
            totals[tc][0] += 1
            totals[tc][1] += int(same(rec["total"], e["total"]))
        # items: match each extracted item to its closest ground-truth item by name
        for it in e["items"]:
            c = it.get("confidence")
            if c not in buckets:
                continue
            best, score = None, 0
            for g in rec["items"]:
                s_ = fuzz.token_set_ratio(it["name"].lower(), g["name"].lower())
                if s_ > score:
                    best, score = g, s_
            ok = best is not None and score >= NAME_THRESHOLD and same(best["line_total"], it["line_total"])
            buckets[c][0] += 1
            buckets[c][1] += int(ok)
    out = {"split": split, "model": model,
           "items": {k: {"n": n, "correct": c, "accuracy": round(c / n, 3) if n else None} for k, (n, c) in buckets.items()},
           "totals": {k: {"n": n, "correct": c, "accuracy": round(c / n, 3) if n else None} for k, (n, c) in totals.items()}}
    (ROOT / "results" / f"calibration_{split}_{model}.json").write_text(json.dumps(out, indent=1))
    print(f"{'confidence':<10}{'items':>8}{'correct':>9}{'accuracy':>10}   {'totals':>7}{'correct':>9}{'accuracy':>10}")
    for k in ("high", "medium", "low"):
        i, t = out["items"][k], out["totals"][k]
        print(f"{k:<10}{i['n']:>8}{i['correct']:>9}{str(i['accuracy']):>10}   {t['n']:>7}{t['correct']:>9}{str(t['accuracy']):>10}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation")
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    a = ap.parse_args()
    main(a.split, a.model)
