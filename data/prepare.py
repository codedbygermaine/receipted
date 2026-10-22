"""Download CORD v2 and write clean ground truth for the validation and test splits.

Outputs:
  data/images/<split>/<id>.png        the receipt photos (gitignored, ~200 files)
  data/gt/<split>.json                one clean record per receipt (committed, small)
  data/train_item_names.txt           item names from the train split, for the synthetic price list

Run:  .venv/bin/python data/prepare.py
"""

import collections
import json
from pathlib import Path

from datasets import load_dataset

from receipted.parsing import parse_price, parse_qty

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "data" / "images"
GT = ROOT / "data" / "gt"
TOLERANCE = 1  # Rupiah; ground truth is in whole rupiah, so this only forgives rounding in the source


def as_list(x):
    """CORD stores a single item as a dict and several as a list. Always return a list."""
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def as_text(x):
    """A name printed over two lines arrives as a list of strings. Join it into one name."""
    if x is None:
        return ""
    if isinstance(x, list):
        return " ".join(str(part).strip() for part in x if part)
    return str(x).strip()


def normalise_items(menu):
    """Flatten menu entries (and their sub-items) into one list of simple line items."""
    items = []
    for raw in as_list(menu):
        items.append({
            "name": as_text(raw.get("nm")),
            "qty": parse_qty(raw.get("cnt")),
            "unit_price": parse_price(raw.get("unitprice")),
            "line_total": parse_price(raw.get("price")),
            "discount": parse_price(raw.get("discountprice")),
            "is_sub_item": False,
        })
        # Sub-items are add-ons (toppings, modifiers) with their own price line on the receipt.
        for sub in as_list(raw.get("sub")):
            if not sub.get("sub_price") and not sub.get("sub_nm"):
                continue
            items.append({
                "name": as_text(sub.get("sub_nm")),
                "qty": parse_qty(sub.get("sub_cnt")),
                "unit_price": parse_price(sub.get("sub_unitprice")),
                "line_total": parse_price(sub.get("sub_price")),
                "discount": None,
                "is_sub_item": True,
            })
    return items


def normalise_receipt(gt_parse):
    sub = gt_parse.get("sub_total", {}) or {}
    tot = gt_parse.get("total", {}) or {}
    return {
        "items": normalise_items(gt_parse.get("menu")),
        "subtotal": parse_price(sub.get("subtotal_price")),
        "tax": parse_price(sub.get("tax_price")),
        "service": parse_price(sub.get("service_price")),
        "discount": parse_price(sub.get("discount_price")),
        "total": parse_price(tot.get("total_price")),
    }


def consistency(rec):
    """Does the ground truth add up on its own? None means 'cannot tell' (a field is missing)."""
    lines = [it["line_total"] for it in rec["items"] if it["line_total"] is not None]
    line_sum = sum(lines) if lines else None

    def close(a, b):
        if a is None or b is None:
            return None
        return abs(a - b) <= TOLERANCE

    expected_total = None
    if rec["subtotal"] is not None:
        expected_total = rec["subtotal"] + (rec["tax"] or 0) + (rec["service"] or 0) - (rec["discount"] or 0)
    return {
        "lines_match_subtotal": close(line_sum, rec["subtotal"]),
        "lines_match_total": close(line_sum, rec["total"]),
        "subtotal_tax_service_match_total": close(expected_total, rec["total"]),
    }


def prepare_split(ds, split):
    out_dir = IMAGES / split
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for i, row in enumerate(ds[split]):
        rid = f"{split}_{i:03d}"
        img_path = out_dir / f"{rid}.png"
        if not img_path.exists():
            row["image"].save(img_path)
        gt_parse = json.loads(row["ground_truth"])["gt_parse"]
        rec = normalise_receipt(gt_parse)
        rec["checks"] = consistency(rec)
        records.append({
            "id": rid,
            "image_path": str(img_path.relative_to(ROOT)),
            "width": row["image"].width,
            "height": row["image"].height,
            **rec,
            "raw": gt_parse,  # kept so any parsing doubt can be checked against the source
        })
    GT.mkdir(parents=True, exist_ok=True)
    (GT / f"{split}.json").write_text(json.dumps(records, indent=1, ensure_ascii=False))
    return records


def print_examples(records, indices):
    for i in indices:
        r = records[i]
        print(f"\n=== {r['id']}  ->  {r['image_path']}  ({r['width']}x{r['height']})")
        print(f"{'qty':>5}  {'unit':>9}  {'line':>9}  name")
        for it in r["items"]:
            prefix = "  + " if it["is_sub_item"] else ""
            print(f"{str(it['qty']):>5}  {str(it['unit_price']):>9}  {str(it['line_total']):>9}  {prefix}{it['name']}")
        print(f"subtotal={r['subtotal']}  tax={r['tax']}  service={r['service']}  "
              f"discount={r['discount']}  total={r['total']}")
        print("checks:", r["checks"])


def print_coverage(records, split):
    n = len(records)
    print(f"\n--- {split}: {n} receipts, {sum(len(r['items']) for r in records)} line items ---")
    for field in ("subtotal", "tax", "service", "discount", "total"):
        have = sum(r[field] is not None for r in records)
        print(f"  {field:<10} present in {have:>3}/{n}")
    for field in ("qty", "unit_price", "line_total"):
        total_items = sum(len(r["items"]) for r in records)
        have = sum(it[field] is not None for r in records for it in r["items"])
        print(f"  item.{field:<10} present in {have:>3}/{total_items} items")
    print("  ground truth adds up?")
    for check in ("lines_match_subtotal", "lines_match_total", "subtotal_tax_service_match_total"):
        vals = [r["checks"][check] for r in records]
        yes, no, unknown = vals.count(True), vals.count(False), vals.count(None)
        print(f"    {check:<34} yes={yes:>3}  no={no:>3}  n/a={unknown:>3}")


def write_train_item_names(ds):
    """Only the text column is read, so the 800 train images are never decoded."""
    counter = collections.Counter()
    for gt in ds["train"]["ground_truth"]:
        menu = json.loads(gt)["gt_parse"].get("menu")
        for it in as_list(menu):
            name = as_text(it.get("nm"))
            if name:
                counter[name] += 1
    path = ROOT / "data" / "train_item_names.txt"
    path.write_text("\n".join(f"{name}\t{c}" for name, c in counter.most_common()))
    print(f"\nWrote {len(counter)} distinct train item names to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    ds = load_dataset("naver-clova-ix/cord-v2")
    val = prepare_split(ds, "validation")
    test = prepare_split(ds, "test")
    print_examples(val, [0, 25, 90])
    print_coverage(val, "validation")
    print_coverage(test, "test")
    write_train_item_names(ds)
