"""Turn the pilot recording sheet into the table for docs/evaluation.md.

Fill results/pilot_sheet.csv during the sessions, one row per claim:
  approver        A or B
  condition       tool  (cleared in the approvals inbox)  |  hand  (receipt photo, claim details and the policy only)
  claim           the claim id or receipt name
  answer_key      approve | reject | review   (fixed before the sessions, not shown to the approvers)
  decision        approve | reject | review   (what the approver did; "review" = held it or asked a question)
  seconds         stopwatch, from opening the claim to the decision
  override        yes if the approver's decision differed from the tool's own decision (tool condition only), else blank
  override_reason the approver's one-sentence reason, verbatim

Usage:  .venv/bin/python eval/pilot_summary.py            (prints Markdown; paste under "Reviewer pilot" in docs/evaluation.md)
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = [r for r in csv.DictReader(open(ROOT / "results" / "pilot_sheet.csv")) if r.get("claim")]
if not rows:
    raise SystemExit("results/pilot_sheet.csv has no rows yet")

by = defaultdict(list)
for r in rows:
    by[r["condition"].strip().lower()].append(r)

def summarise(rs):
    n = len(rs)
    correct = [r for r in rs if r["decision"].strip().lower() == r["answer_key"].strip().lower()]
    secs = [float(r["seconds"]) for r in rs if r["seconds"].strip()]
    unnecessary = [r for r in rs if r["answer_key"].strip().lower() == "approve" and r["decision"].strip().lower() == "review"]
    per_correct = (sum(float(r["seconds"]) for r in correct if r["seconds"].strip()) / len(correct)) if correct else None
    return {"claims": n, "correct": len(correct), "mean_seconds": sum(secs) / len(secs) if secs else None,
            "seconds_per_correct_decision": per_correct, "unnecessary_reviews": len(unnecessary)}

print("| | with Receipted | by hand |\n|---|---|---|")
tool, hand = summarise(by.get("tool", [])), summarise(by.get("hand", []))
fmt = lambda v: "n/a" if v is None else (f"{v:.0f} s" if isinstance(v, float) else str(v))
for key, label in [("claims", "claims"), ("correct", "correct decisions"), ("mean_seconds", "mean time per claim"),
                   ("seconds_per_correct_decision", "mean time per correct decision"), ("unnecessary_reviews", "clean claims held or questioned")]:
    print(f"| {label} | {fmt(tool[key])} | {fmt(hand[key])} |")
overrides = [r for r in by.get("tool", []) if r["override"].strip().lower() == "yes"]
print(f"\nOverrides of the tool's decision: {len(overrides)} of {tool['claims']}")
for r in overrides:
    print(f"- {r['approver']}, {r['claim']}: {r['override_reason'].strip()}")
approvers = sorted({r["approver"] for r in rows})
print(f"\nApprovers: {len(approvers)}. Claims per approver: " + ", ".join(f"{a} {sum(1 for r in rows if r['approver'] == a)}" for a in approvers) + ". A pilot, not a validation.")
