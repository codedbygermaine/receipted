"""Run the full agent on every claim in a split and score it against the labels.

Reports, per planted error type, how many were caught (recall); false alarms on clean claims;
decision accuracy; and how many rule-check issues the verifier dropped.

Usage: .venv/bin/python eval/eval_checks.py --split validation --limit 10
       .venv/bin/python eval/eval_checks.py --split test --yes
"""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

from receipted import llm
from receipted.graph import run_claim

ROOT = Path(__file__).resolve().parents[1]
CLAIM_FIELDS = ("claim_id", "submitter", "purpose", "amount", "currency", "items")  # labels never reach the agent
EST_TOKENS_PER_CLAIM = {"input": 7000, "output": 1200}  # extraction + rule check + draft, measured on validation


def caught(label, planted_detail, issues) -> bool:
    """Did any verified issue correspond to this label?"""
    types = {i["type"] for i in issues}
    clauses = {i.get("clause_id") for i in issues if i["source"] == "rules"}
    has_price = any(i.get("price_item") for i in issues)
    return {
        "inflated_amount": "claim_exceeds_receipt" in types or "C4" in clauses,
        "wrong_quantity": "claimed_qty_exceeds_receipt" in types or "C9" in clauses,
        "item_not_on_receipt": "claimed_item_not_on_receipt" in types,
        "totals_mismatch": "claim_lines_vs_amount" in types,
        "policy_breach": (planted_detail or {}).get("clause") in clauses,
        "price_above_list": has_price or "C5" in clauses,
        "alcohol_on_receipt": "C3" in clauses,
        "above_500k": "C7" in clauses,
        "packaging_over_5000": "C13" in clauses,
        "receipt_inconsistent": bool(types & {"lines_vs_totals", "totals_arithmetic"}),
    }[label]


def main(split, model, limit, yes):
    claims = json.load(open(ROOT / "data" / "claims" / f"{split}.json"))
    if limit:
        claims = claims[:limit]
    if split == "test" and not yes:
        inp, out = llm.PRICES_PER_MTOK[model]
        est = len(claims) * (EST_TOKENS_PER_CLAIM["input"] * inp + EST_TOKENS_PER_CLAIM["output"] * out) / 1e6
        print(f"ESTIMATE: {len(claims)} claims x 3 LLM calls each on {model} ≈ ${est:.2f} "
              f"(extraction is free if eval_extraction already ran). Re-run with --yes to proceed.")
        return

    rows = []
    for c in claims:
        agent_claim = {k: c[k] for k in CLAIM_FIELDS}
        state = run_claim(ROOT / c["image_path"], agent_claim, model=model)
        labels = c["labels"]
        issues = state["verified_issues"]
        all_labels = ([labels["planted_error"]] if labels["planted_error"] else []) + labels["natural_flags"]
        row = {
            "claim_id": c["claim_id"], "receipt_id": c["receipt_id"], "image_path": c["image_path"],
            "planted_error": labels["planted_error"], "planted_detail": labels["planted_detail"],
            "natural_flags": labels["natural_flags"],
            "expected": labels["expected_decision"], "predicted": state["decision"],
            "decision_reason": state["decision_reason"],
            "submitter": c["submitter"], "claimed_amount": c["amount"], "currency": c["currency"],
            "receipt_total": (state.get("receipt") or {}).get("total"),
            "readability": (state.get("receipt") or {}).get("readability"),
            "extraction_error": state.get("error"),
            "caught": {l: caught(l, labels["planted_detail"], issues) for l in all_labels},
            "verified_issues": [{k: i.get(k) for k in ("source", "type", "severity", "clause_id", "price_item", "receipt_line", "message", "evidence")} for i in issues],
            "n_rule_issues": len(state.get("rule_issues", [])),
            "n_dropped": len(state["dropped_issues"]),
            "dropped": [{"type": d["type"], "clause_id": d["clause_id"], "price_item": d["price_item"],
                         "receipt_line": d["receipt_line"], "why": d["dropped_because"]} for d in state["dropped_issues"]],
            "draft": state["draft"],
            "cost_usd": state["total_cost_usd"], "seconds": state["total_seconds"],
            "cached": all(e.get("cached") for e in state["trace"] if "cost_usd" in e),
        }
        rows.append(row)
        mark = "ok " if row["predicted"] == row["expected"] else "XX "
        print(f"  {mark}{row['claim_id']} {row['planted_error'] or 'clean':<20} {str(row['natural_flags']):<30} "
              f"expected={row['expected']:<12} got={row['predicted']:<12} issues={[i['type'] for i in issues]} dropped={row['n_dropped']}")

    # --- metrics ---
    per_type = {}
    for t in ["inflated_amount", "wrong_quantity", "item_not_on_receipt", "totals_mismatch", "policy_breach"]:
        rs = [r for r in rows if r["planted_error"] == t]
        per_type[t] = {"n": len(rs), "caught": sum(r["caught"][t] for r in rs),
                       "recall": round(sum(r["caught"][t] for r in rs) / len(rs), 4) if rs else None,
                       "decision_not_approve": sum(r["predicted"] != "approve" for r in rs)}
    natural = {}
    for f in ["price_above_list", "alcohol_on_receipt", "above_500k", "packaging_over_5000", "receipt_inconsistent"]:
        rs = [r for r in rows if f in r["natural_flags"]]
        natural[f] = {"n": len(rs), "caught": sum(r["caught"][f] for r in rs),
                      "recall": round(sum(r["caught"][f] for r in rs) / len(rs), 4) if rs else None}

    clean = [r for r in rows if not r["planted_error"] and not r["natural_flags"]]
    fa_with_issue = [r for r in clean if r["verified_issues"]]
    fa_readability_only = [r for r in clean if not r["verified_issues"] and r["predicted"] != "approve"]
    false_alarms = {
        "n_clean_claims": len(clean),
        "flagged_with_an_issue": len(fa_with_issue),
        "held_for_readability_only": len(fa_readability_only),
        "false_alarm_rate_issues": round(len(fa_with_issue) / len(clean), 4) if clean else None,
        "false_alarm_rate_any": round((len(fa_with_issue) + len(fa_readability_only)) / len(clean), 4) if clean else None,
        "false_alarm_issue_types": dict(Counter(i["type"] for r in fa_with_issue for i in r["verified_issues"])),
    }
    confusion = Counter((r["expected"], r["predicted"]) for r in rows)
    summary = {
        "split": split, "model": model, "n_claims": len(rows),
        "decision_accuracy": round(sum(r["predicted"] == r["expected"] for r in rows) / len(rows), 4),
        "confusion_expected_to_predicted": {f"{e}->{p}": n for (e, p), n in sorted(confusion.items())},
        "planted": per_type,
        "natural": natural,
        "false_alarms": false_alarms,
        "verifier": {"rule_issues_raised": sum(r["n_rule_issues"] for r in rows),
                     "dropped": sum(r["n_dropped"] for r in rows),
                     "drop_reasons": dict(Counter(d["why"].split(" ")[0] + "..." if "unit price" in d["why"] else d["why"] for r in rows for d in r["dropped"]))},
        "mean_cost_usd_per_claim": round(statistics.mean(r["cost_usd"] for r in rows), 5),
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 4),
        "mean_seconds_per_claim_uncached": round(statistics.mean([r["seconds"] for r in rows if not r["cached"]]), 2) if any(not r["cached"] for r in rows) else None,
        "readability_counts": dict(Counter(r["readability"] for r in rows)),
    }
    out = ROOT / "results" / f"checks_{split}_{model}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "claims": rows}, indent=1, ensure_ascii=False))
    print("\nSUMMARY")
    print(json.dumps(summary, indent=1))
    print(f"written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation", choices=["validation", "test"])
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    main(a.split, a.model, a.limit, a.yes)
