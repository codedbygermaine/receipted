"""CLI: python -m receipted.run --image data/images/validation/validation_025.png --claim my_claim.json
     or: python -m receipted.run --sample SAMPLE-002        (uses fixtures/sample_claims.json)
Add --model claude-opus-5-5 to use the larger model, --json to dump the full state.
"""

import argparse
import json
from pathlib import Path

from receipted import llm
from receipted.graph import run_claim

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image")
    ap.add_argument("--claim", help="path to a JSON file holding one claim object")
    ap.add_argument("--sample", help="claim_id from fixtures/sample_claims.json")
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    ap.add_argument("--json", action="store_true", help="print the full final state as JSON")
    args = ap.parse_args()

    if args.sample:
        claims = {c["claim_id"]: c for c in json.load(open(ROOT / "fixtures" / "sample_claims.json"))}
        claim = claims[args.sample]
        gt = {r["id"]: r for s in ("validation", "test") for r in json.load(open(ROOT / "data" / "gt" / f"{s}.json"))}
        image = ROOT / gt[claim["receipt_id"]]["image_path"]
    else:
        if not (args.image and args.claim):
            ap.error("give --image and --claim, or --sample")
        claim, image = json.load(open(args.claim)), args.image

    state = run_claim(image, claim, model=args.model, register=True)

    if args.json:
        print(json.dumps({k: v for k, v in state.items() if k != "retrieved"}, indent=1, ensure_ascii=False, default=str))
        return

    print(f"\nDECISION: {state['decision'].upper()}  ({state['decision_reason']})")
    print(f"\nISSUES ({len(state['verified_issues'])} verified, {len(state['dropped_issues'])} dropped by verifier):")
    for i in state["verified_issues"]:
        cite = i["clause_id"] or i["price_item"] or "code"
        print(f"  [{i['severity']:>6}] {i['type']:<28} {cite:<10} {i['message']}")
        if i.get("receipt_line"):
            print(f"           line: {i['receipt_line']!r}")
    print(f"\nDRAFT MESSAGE:\n{state['draft']}")
    print("\nTRACE:")
    for e in state["trace"]:
        cost = f"  ${e['cost_usd']:.4f}" + (" (cached)" if e.get("cached") else "") if e.get("cost_usd") is not None else ""
        print(f"  {e['node']:<12} {e['seconds']:>6.2f}s{cost:<20} {e['summary']}")
    print(f"\nTotal: {state['total_seconds']}s, ${state['total_cost_usd']:.4f} ({state['model']})")


if __name__ == "__main__":
    main()
