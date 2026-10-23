"""Collect the eval outputs into results/metrics.json, a markdown results table, two charts and a
fact sheet for the error analysis. Every number comes from the JSON files the eval scripts wrote.

Usage: .venv/bin/python eval/report.py --split test
"""

import argparse
import datetime as dt
import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats import bootstrap_ci, fmt_ci  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
# categorical palette (validated, see dataviz reference): slot 1 blue, slot 2 orange; fixed per model
COLORS = {"claude-haiku-5-5": "#2a78d6", "claude-opus-5-5": "#eb6834", "claude-sonnet-5-5": "#1baf7a"}
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"


def load(pattern):
    out = {}
    for path in sorted(glob.glob(str(RES / pattern))):
        d = json.load(open(path))
        out[d["summary"]["model"] if "model" in d["summary"] else d["summary"]["agent_model"]] = d
    return out


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d6d5d0")
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="x", color="#e8e7e2", linewidth=0.6)
    ax.set_axisbelow(True)


def chart_recall(checks, split):
    s = checks["summary"]
    labels, values, ns = [], [], []
    for name, d in list(s["planted"].items()) + [(k, v) for k, v in s["natural"].items() if v["n"]]:
        labels.append(name.replace("_", " ") + ("" if name in s["planted"] else " (natural)"))
        values.append((d["recall"] or 0) * 100)
        ns.append(f"{d['caught']}/{d['n']}")
    fig, ax = plt.subplots(figsize=(7.5, 0.45 * len(labels) + 1.4), facecolor=SURFACE)
    style(ax)
    y = range(len(labels))[::-1]
    ax.barh(list(y), values, height=0.55, color=COLORS[s["model"]])
    for yi, v, n in zip(y, values, ns):
        ax.text(min(v, 100) + 1.5, yi, f"{v:.0f}%  ({n})", va="center", fontsize=9, color=INK)
    ax.set_yticks(list(y)); ax.set_yticklabels(labels, color=INK)
    ax.set_xlim(0, 118); ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("errors caught (recall)", color=INK2, fontsize=9)
    ax.set_title(f"Errors caught per type ({split}, {s['model'].replace('claude-', '')}, n={s['n_claims']} claims)", loc="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(RES / f"chart_recall_{split}.png", dpi=160)
    plt.close(fig)


def chart_models(extraction, split):
    models = list(extraction)
    panels = [("item_f1", "item F1", lambda v: f"{v:.2f}"),
              ("total_accuracy", "total correct", lambda v: f"{v:.0%}"),
              ("mean_latency_s", "mean seconds / receipt", lambda v: f"{v:.1f}s"),
              ("mean_cost_usd", "mean cost / receipt", lambda v: f"${v:.4f}")]
    fig, axes = plt.subplots(1, len(panels), figsize=(2.6 * len(panels), 3.2), facecolor=SURFACE)
    for ax, (key, title, fmt) in zip(axes, panels):
        style(ax); ax.grid(False)
        vals = [extraction[m]["summary"][key] or 0 for m in models]
        ax.bar(range(len(models)), vals, width=0.55, color=[COLORS.get(m, "#888") for m in models])
        for i, v in enumerate(vals):
            ax.text(i, v, " " + fmt(v), ha="center", va="bottom", fontsize=9, color=INK)
        ax.set_xticks(range(len(models))); ax.set_xticklabels([m.replace("claude-", "") for m in models], fontsize=8, color=INK)
        ax.set_ylim(0, max(vals) * 1.3 if max(vals) else 1); ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        ax.set_title(title, fontsize=10, loc="left", color=INK)
    fig.suptitle(f"Extraction by model, {split} split (n={extraction[models[0]]['summary']['n_receipts']} receipts)",
                 x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(RES / f"chart_models_{split}.png", dpi=160)
    plt.close(fig)


def pct(x):
    return "n/a" if x is None else f"{x * 100:.0f}%"


def results_table(extraction, checks, drafts, split):
    md = [f"## Results ({split} split)\n", "### Extraction vs CORD ground truth\n",
          "| model | receipts | item F1 (95% CI) | item precision | item recall | total correct | subtotal correct | tax correct | mean latency | mean cost / receipt |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for m, d in extraction.items():
        s = d["summary"]
        rows = d["receipts"]
        def f1_of(rs):
            hits = sum(r["full_hits"] for r in rs); ex = sum(r["n_extracted_items"] for r in rs); gt = sum(r["n_gt_items"] for r in rs)
            p_ = hits / ex if ex else 0; r_ = hits / gt if gt else 0
            return 2 * p_ * r_ / (p_ + r_) if p_ + r_ else 0
        f1, lo, hi = bootstrap_ci(rows, statistic=f1_of)
        md.append(f"| `{m}` | {s['n_receipts']} | {fmt_ci(f1, lo, hi, pct=False)} | {s['item_precision']:.2f} | {s['item_recall']:.2f} | "
                  f"{pct(s['total_accuracy'])} | {pct(s['subtotal_accuracy'])} | {pct(s['tax_accuracy'])} | "
                  f"{s['mean_latency_s']}s | ${s['mean_cost_usd']:.4f} |")
    if checks:
        s = checks["summary"]
        rows = checks["claims"]
        md += [f"\n### Checks: full agent on {s['n_claims']} synthetic claims (`{s['model']}`)\n",
               "| planted error | n | caught | recall (95% CI) |", "|---|---|---|---|"]
        for t, d in s["planted"].items():
            flags = [1 if r["caught"].get(t) else 0 for r in rows if r["planted_error"] == t]
            md.append(f"| {t.replace('_', ' ')} | {d['n']} | {d['caught']} | {fmt_ci(*bootstrap_ci(flags))} |")
        all_flags = [1 if r["caught"].get(r["planted_error"]) else 0 for r in rows if r["planted_error"]]
        md.append(f"| **all planted errors** | {len(all_flags)} | {sum(all_flags)} | **{fmt_ci(*bootstrap_ci(all_flags))}** |")
        md += ["\n| natural breach (from ground truth) | n | caught | recall |", "|---|---|---|---|"]
        md += [f"| {t.replace('_', ' ')} | {d['n']} | {d['caught']} | {pct(d['recall'])} |" for t, d in s["natural"].items() if d["n"]]
        fa = s["false_alarms"]
        dec = [1 if r["predicted"] == r["expected"] else 0 for r in rows]
        clean = [r for r in rows if not r["planted_error"] and not r["natural_flags"]]
        fa_flags = [1 if r["verified_issues"] else 0 for r in clean]
        md += ["\n| metric | value |", "|---|---|",
               f"| decision accuracy (approve / needs_review / reject) | {fmt_ci(*bootstrap_ci(dec))} |",
               f"| clean claims (no planted error, no natural breach) | {fa['n_clean_claims']} |",
               f"| false alarms: clean claim flagged with an issue | {fa['flagged_with_an_issue']} ({fmt_ci(*bootstrap_ci(fa_flags))}) |",
               f"| clean claims held only because the receipt was hard to read | {fa['held_for_readability_only']} |",
               f"| rule-check issues raised / dropped by verifier | {s['verifier']['rule_issues_raised']} / {s['verifier']['dropped']} |",
               f"| mean cost per claim | ${s['mean_cost_usd_per_claim']:.4f} |",
               f"| mean seconds per claim (uncached) | {s['mean_seconds_per_claim_uncached']} |"]
    run1 = sorted(glob.glob(str(RES / f"run1_checks_{split}_*.json")))
    if run1 and checks:
        r1 = json.load(open(run1[0]))["summary"]; r2 = checks["summary"]
        def line(name, f):
            return f"| {name} | {f(r1)} | {f(r2)} |"
        md += ["\n### Run 1 vs run 2 (same test claims, before and after the fixes from the error analysis)\n",
               "| metric | run 1 | run 2 |", "|---|---|---|",
               line("planted errors caught", lambda x: f"{sum(v['caught'] for v in x['planted'].values())}/{sum(v['n'] for v in x['planted'].values())}"),
               line("decision accuracy", lambda x: pct(x["decision_accuracy"])),
               line("false alarms (clean claims flagged)", lambda x: f"{x['false_alarms']['flagged_with_an_issue']}/{x['false_alarms']['n_clean_claims']}"),
               line("rule-check issues dropped by verifier", lambda x: str(x["verifier"]["dropped"])),
               line("mean cost per claim", lambda x: f"${x['mean_cost_usd_per_claim']:.4f}"),
               "\nRun 2 is reported because the three fixes were motivated by failures seen in run 1; both are kept so the effect is visible and the second run is not mistaken for a first."]
    if drafts:
        s = drafts["summary"]
        md += [f"\n### Drafts: LLM-as-judge (`{s['judge_model']}` scoring `{s['agent_model']}` drafts, 1–5)\n",
               "| accuracy | evidence | clarity | tone | drafts with accuracy < 4 |", "|---|---|---|---|---|",
               f"| {s['mean_accuracy']} | {s['mean_evidence']} | {s['mean_clarity']} | {s['mean_tone']} | {s['n_accuracy_below_4']} / {s['n_drafts']} |"]
        agr = s.get("human_vs_judge_agreement")
        if agr and "n" in agr:
            md += ["\n| human vs judge (10 drafts) | exact agreement | within 1 point |", "|---|---|---|"]
            md += [f"| {d} | {pct(agr[d]['exact_agreement'])} | {pct(agr[d]['within_1'])} |" for d in ("accuracy", "evidence", "clarity", "tone")]
        else:
            md.append("\n_Human scoring sheet generated; agreement will be reported once it is filled in._")
    return "\n".join(md) + "\n"


def failure_facts(checks, extraction):
    """Pick up to 5 real failures for the error analysis, worst first."""
    rows = checks["claims"]
    wrong = [r for r in rows if r["predicted"] != r["expected"]]
    missed = [r for r in wrong if r["planted_error"] and not r["caught"].get(r["planted_error"])]
    false_alarm = [r for r in wrong if not r["planted_error"] and not r["natural_flags"]]
    other = [r for r in wrong if r not in missed and r not in false_alarm]
    picked = (missed + false_alarm + other)[:5]
    facts = []
    for r in picked:
        facts.append({"kind": "missed planted error" if r in missed else "false alarm" if r in false_alarm else "wrong decision",
                      "claim_id": r["claim_id"], "receipt_id": r["receipt_id"], "image": r["image_path"],
                      "planted": r["planted_error"], "planted_detail": r["planted_detail"], "natural": r["natural_flags"],
                      "expected": r["expected"], "predicted": r["predicted"], "reason": r["decision_reason"],
                      "readability": r["readability"],
                      "issues": [(i["type"], i["clause_id"] or i["price_item"], i["message"]) for i in r["verified_issues"]],
                      "dropped": r["dropped"]})
    if len(facts) < 5 and extraction:
        ex = list(extraction.values())[0]["receipts"]
        bad = sorted([e for e in ex if not e["total_ok"] or e["full_hits"] < e["n_gt_items"]],
                     key=lambda e: (e["total_ok"], e["full_hits"] / max(e["n_gt_items"], 1)))
        for e in bad[: 5 - len(facts)]:
            facts.append({"kind": "extraction error", "receipt_id": e["id"], "model": e["model"],
                          "items_exact": f"{e['full_hits']}/{e['n_gt_items']}", "names_matched": f"{e['name_hits']}/{e['n_gt_items']}",
                          "extracted_items": e["n_extracted_items"], "total_ok": e["total_ok"], "readability": e["readability"]})
    return facts


def main(split):
    extraction = load(f"extraction_{split}_*.json")
    checks_all = load(f"checks_{split}_*.json")
    drafts_all = load(f"drafts_{split}_*.json")
    checks = next(iter(checks_all.values()), None)
    drafts = next(iter(drafts_all.values()), None)
    metrics = {
        "split": split, "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "extraction": {m: d["summary"] for m, d in extraction.items()},
        "checks": checks["summary"] if checks else None,
        "drafts": drafts["summary"] if drafts else None,
    }
    (RES / "metrics.json").write_text(json.dumps(metrics, indent=1))
    (RES / "results_table.md").write_text(results_table(extraction, checks, drafts, split))
    if checks:
        chart_recall(checks, split)
        facts = failure_facts(checks, extraction)
        (RES / "error_analysis_facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False))
    if extraction:
        chart_models(extraction, split)
    print((RES / "results_table.md").read_text())
    print("wrote results/metrics.json, results_table.md, charts and error_analysis_facts.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    main(ap.parse_args().split)
