"""Hallucination probe: hide the printed total on real receipts and see whether the model says null
(honest: "not printed") or returns a number (invented, or computed against instructions).

CORD's raw labels give pixel coordinates for every printed word, so the total can be painted over
exactly. Usage: .venv/bin/python eval/hallucination_probe.py --split validation --limit 10
"""

import argparse
import json
from pathlib import Path

from datasets import load_dataset
from PIL import Image, ImageDraw

from receipted import llm
from receipted.extract import ExtractionError, extract
from receipted.maths import close

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe"
CATEGORY = "total.total_price"


def mask_total(image: Image.Image, ground_truth: dict) -> tuple[Image.Image, int]:
    """Paint white over every word labelled as the total. Returns (image, words_masked)."""
    img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    n = 0
    for line in ground_truth.get("valid_line", []):
        if line.get("category") != CATEGORY:
            continue
        for w in line.get("words", []):
            q = w["quad"]
            xs, ys = [q[f"x{i}"] for i in range(1, 5)], [q[f"y{i}"] for i in range(1, 5)]
            pad = 6
            draw.rectangle([min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad], fill="white")
            n += 1
    return img, n


def main(split, limit, model):
    ds = load_dataset("naver-clova-ix/cord-v2")[split]
    gt = json.load(open(ROOT / "data" / "gt" / f"{split}.json"))
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(len(ds)):
        if len(rows) >= limit:
            break
        rec = gt[i]
        if rec["total"] is None:
            continue
        raw = json.loads(ds[i]["ground_truth"])
        img, n_words = mask_total(ds[i]["image"], raw)
        if n_words == 0:
            continue
        path = OUT / f"{rec['id']}_masked_total.png"
        img.save(path)
        try:
            r = extract(path, model=model)
            got = r.receipt["total"]
            readability = r.receipt["readability"]
        except ExtractionError as e:
            got, readability = f"error: {e}", None
        if got is None:
            verdict = "abstained"
        elif isinstance(got, (int, float)) and close(got, rec["total"]):
            verdict = "produced the true total anyway"
        else:
            verdict = "invented a different number"
        rows.append({"id": rec["id"], "true_total": rec["total"], "returned_total": got, "verdict": verdict,
                     "readability": readability, "masked_words": n_words, "image": str(path.relative_to(ROOT))})
        print(f"  {rec['id']}: true={rec['total']} returned={got} -> {verdict} ({readability})")
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    summary = {"split": split, "model": model, "n": len(rows), "verdicts": counts,
               "abstention_rate": round(counts.get("abstained", 0) / len(rows), 3) if rows else None}
    (ROOT / "results" / f"hallucination_probe_{split}_{model}.json").write_text(json.dumps({"summary": summary, "receipts": rows}, indent=1))
    print("\nSUMMARY", json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    a = ap.parse_args()
    main(a.split, a.limit, a.model)
