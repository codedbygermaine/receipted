"""Regression gate: compare two runs of eval_checks (same split) claim by claim.

Usage: .venv/bin/python eval/compare.py results/run1_checks_test_claude-haiku-5-5.json results/checks_test_claude-haiku-5-5.json
Exit code 1 if planted-error recall or decision accuracy dropped, or false alarms rose.
"""

import json
import sys


def main(base_path, cand_path):
    base, cand = json.load(open(base_path)), json.load(open(cand_path))
    b_rows = {r["claim_id"]: r for r in base["claims"]}
    c_rows = {r["claim_id"]: r for r in cand["claims"]}
    ids = sorted(set(b_rows) & set(c_rows))
    print(f"comparing {len(ids)} claims: {base_path}  ->  {cand_path}\n")

    changed = [i for i in ids if b_rows[i]["predicted"] != c_rows[i]["predicted"]]
    print(f"decisions changed: {len(changed)}")
    for i in changed:
        b, c = b_rows[i], c_rows[i]
        better = (c["predicted"] == c["expected"]) and (b["predicted"] != b["expected"])
        worse = (b["predicted"] == b["expected"]) and (c["predicted"] != c["expected"])
        tag = "FIXED" if better else "BROKE" if worse else "moved"
        print(f"  {tag:<6} {i} {b['planted_error'] or 'clean':<20} expected={c['expected']:<12} {b['predicted']} -> {c['predicted']}  "
              f"issues: {[x['type'] for x in b['verified_issues']]} -> {[x['type'] for x in c['verified_issues']]}")

    def headline(d):
        s = d["summary"]
        planted = s["planted"]
        caught = sum(v["caught"] for v in planted.values()); n = sum(v["n"] for v in planted.values())
        return {"recall": caught / n if n else 0, "decision_accuracy": s["decision_accuracy"],
                "false_alarm_rate": s["false_alarms"]["false_alarm_rate_issues"] or 0,
                "dropped": s["verifier"]["dropped"], "cost": s["total_cost_usd"]}

    hb, hc = headline(base), headline(cand)
    print("\nheadline            base      candidate")
    for k in hb:
        print(f"  {k:<18}{hb[k]:>8.3f}  {hc[k]:>8.3f}")
    regressed = hc["recall"] < hb["recall"] or hc["decision_accuracy"] < hb["decision_accuracy"] or hc["false_alarm_rate"] > hb["false_alarm_rate"]
    print("\nRESULT:", "REGRESSION" if regressed else "no regression")
    return 1 if regressed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
