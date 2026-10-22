"""Run the whole check pipeline (without the graph yet) on the sample claims and show every issue
with its evidence. Usage: .venv/bin/python scripts/try_checks.py [model]
"""

import json
import sys
from pathlib import Path

from receipted import llm, maths
from receipted.extract import extract
from receipted.retrieve import load_policy_clauses, load_price_list, retrieve_for
from receipted.rules import check_rules
from receipted.verify import verify

ROOT = Path(__file__).resolve().parents[1]
model = sys.argv[1] if len(sys.argv) > 1 else llm.DEFAULT_MODEL

gt = {r["id"]: r for split in ("validation", "test") for r in json.load(open(ROOT / "data" / "gt" / f"{split}.json"))}
claims = json.load(open(ROOT / "fixtures" / "sample_claims.json"))
clauses, price_list = load_policy_clauses(), load_price_list()

for claim in claims:
    rec = gt[claim["receipt_id"]]
    ex = extract(ROOT / rec["image_path"], model=model)
    receipt = ex.receipt
    m_issues = maths.check_receipt(receipt) + maths.check_claim(claim, receipt)
    retrieved = retrieve_for(receipt, claim)
    r_issues, meta = check_rules(receipt, claim, m_issues, retrieved, model=model)
    kept, dropped = verify(m_issues + r_issues, receipt, clauses, price_list)

    print(f"\n{'=' * 100}\n{claim['claim_id']}  receipt={claim['receipt_id']}  claimed={claim['amount']}  "
          f"receipt_total={receipt['total']}  readability={receipt['readability']}")
    print(f"  {claim['note']}")
    print(f"  retrieved clauses: {[c['id'] for c in retrieved['clauses']]}   "
          f"rule-check: {meta['input_tokens']} in / {meta['output_tokens']} out, ${meta['cost_usd']:.4f}, cached={meta['cached']}")
    print(f"  issues: maths={len(m_issues)} rules={len(r_issues)} -> verified={len(kept)} dropped={len(dropped)}")
    for i in kept:
        cite = i["clause_id"] or i["price_item"] or "code"
        print(f"   [{i['severity']:>6}] {i['type']:<28} cites {cite:<12} line: {i['receipt_line']!r}")
        print(f"           {i['message']}")
        ev = {k: v for k, v in i["evidence"].items() if k != "clause_text"}
        if ev:
            print(f"           evidence: {ev}")
        if "clause_text" in i["evidence"]:
            print(f"           clause: {i['evidence']['clause_text'][:110]}...")
    for d in dropped:
        print(f"   DROPPED {d['type']} (cites {d['clause_id'] or d['price_item']}, line {d['receipt_line']!r}): {d['dropped_because']}")
