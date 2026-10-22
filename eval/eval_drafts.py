"""LLM-as-a-judge for the draft messages, plus a sheet for a human to score 10 of them by hand.

The judge (a larger, different model from the one that wrote the drafts) sees the claim, the
verified issues, the decision and the draft, and scores 1-5 on four dimensions with a written rubric.
If results/human_scores.csv has been filled in, agreement between human and judge is reported.

Usage: .venv/bin/python eval/eval_drafts.py --split validation --limit 10
       .venv/bin/python eval/eval_drafts.py --split test --yes
"""

import argparse
import csv
import json
import random
import statistics
import time
from typing import Literal

from pydantic import BaseModel, Field

from receipted import llm
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JUDGE_MODEL = llm.LARGE_MODEL
PROMPT_VERSION = "v2"
SEED = 20261023

RUBRIC = """Score each dimension from 1 to 5.

ACCURACY — does the message state only what the verified issues and decision say?
 5: every number, item, clause id and the decision match the facts exactly; nothing added.
 3: one small slip (a rounded number, a clause id missing) but no invented problem.
 1: states a problem or fact that is not in the verified issues, or gets the decision wrong.

EVIDENCE — does each problem mentioned point at its evidence?
 5: each problem gives the numbers involved (claimed vs receipt, qty, price) and the clause id or receipt line.
 3: problems are named but some evidence (a number or clause) is left out.
 1: problems are asserted with no numbers or clauses, or evidence is mismatched to the wrong problem.

CLARITY — could the member act on it without asking a question?
 5: each problem is one clear point with what to do next; no duplication; under about 150 words.
 3: understandable but repetitive, vague on next steps, or overly long.
 1: confusing, contradictory, or the required action is unclear.

TONE — polite, neutral, treasurer-to-member.
 5: courteous and matter-of-fact; no accusation, no apology spiral, no jargon.
 3: slightly stiff or slightly too casual, or one awkward phrase.
 1: accusatory, sarcastic, or inappropriate."""

SYSTEM_PROMPT = "You are a strict reviewer scoring a treasurer's message to a club member using the rubric below. " \
                "Judge only against the FACTS given; anything in the message not supported by them is an accuracy error.\n\n" + RUBRIC


class Scores(BaseModel):
    accuracy: Literal[1, 2, 3, 4, 5]
    evidence: Literal[1, 2, 3, 4, 5]
    clarity: Literal[1, 2, 3, 4, 5]
    tone: Literal[1, 2, 3, 4, 5]
    justification: str = Field(description="One or two sentences, naming any unsupported statement")


def judge(row: dict, model: str) -> tuple[dict, dict]:
    facts = {
        "claim_id": row["claim_id"], "submitter": row["submitter"], "claimed_amount": row["claimed_amount"],
        "currency": row["currency"], "receipt_total": row["receipt_total"],
        "decision": row["predicted"], "decision_reason": row["decision_reason"],
        "verified_issues": row["verified_issues"],
    }
    user = f"FACTS:\n{json.dumps(facts, ensure_ascii=False, indent=1)}\n\nMESSAGE TO SCORE:\n{row['draft']}"
    key = llm.cache_key(user, PROMPT_VERSION, model, SYSTEM_PROMPT)
    hit = llm.cache_get("judge", key)
    if hit:
        return hit["scores"], {**hit["meta"], "cached": True}
    t0 = time.perf_counter()
    resp = llm.client().messages.parse(model=model, max_tokens=4000, system=SYSTEM_PROMPT,
                                       messages=[{"role": "user", "content": user}],
                                       output_format=Scores, output_config={"effort": "medium"})
    scores = resp.parsed_output.model_dump()
    meta = {"model": model, "input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens,
            "latency_s": round(time.perf_counter() - t0, 2),
            "cost_usd": round(llm.cost_usd(model, resp.usage.input_tokens, resp.usage.output_tokens), 6), "cached": False}
    llm.cache_put("judge", key, {"scores": scores, "meta": meta})
    return scores, meta


def write_human_sheet(rows, split):
    rng = random.Random(SEED)
    sample = rng.sample(rows, min(10, len(rows)))
    md = [f"# Human scoring sheet ({split}) — score 1-5 per dimension using the rubric below\n", RUBRIC, "\n---\n"]
    for r in sample:
        md.append(f"## {r['claim_id']}  (decision: {r['predicted']})\n")
        md.append("**Verified issues (the only facts the message may use):**\n")
        md += [f"- [{i['severity']}] {i['type']} ({i['clause_id'] or i['price_item'] or 'code'}): {i['message']}" for i in r["verified_issues"]] or ["- none"]
        md.append(f"\n**Message:**\n\n> " + r["draft"].replace("\n", "\n> ") + "\n")
        md.append("Accuracy: __   Evidence: __   Clarity: __   Tone: __\n\n---\n")
    (ROOT / "results" / f"human_scoring_sheet_{split}.md").write_text("\n".join(md))
    csv_path = ROOT / "results" / f"human_scores_{split}.csv"
    if not csv_path.exists():
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["claim_id", "accuracy", "evidence", "clarity", "tone"])
            for r in sample:
                w.writerow([r["claim_id"], "", "", "", ""])
    return [r["claim_id"] for r in sample]


def agreement(judged, split):
    csv_path = ROOT / "results" / f"human_scores_{split}.csv"
    if not csv_path.exists():
        return None
    human = [r for r in csv.DictReader(open(csv_path)) if r["accuracy"].strip()]
    if not human:
        return {"status": "human_scores not filled in yet"}
    by_id = {j["claim_id"]: j["scores"] for j in judged}
    out = {"n": len(human)}
    for dim in ("accuracy", "evidence", "clarity", "tone"):
        pairs = [(int(h[dim]), by_id[h["claim_id"]][dim]) for h in human if h["claim_id"] in by_id]
        out[dim] = {"exact_agreement": round(sum(a == b for a, b in pairs) / len(pairs), 3),
                    "within_1": round(sum(abs(a - b) <= 1 for a, b in pairs) / len(pairs), 3),
                    "human_mean": round(statistics.mean(a for a, _ in pairs), 2),
                    "judge_mean": round(statistics.mean(b for _, b in pairs), 2)}
    return out


def main(split, agent_model, judge_model, limit, yes):
    src = ROOT / "results" / f"checks_{split}_{agent_model}.json"
    rows = json.load(open(src))["claims"]
    if limit:
        rows = rows[:limit]
    if split == "test" and not yes:
        inp, out = llm.PRICES_PER_MTOK[judge_model]
        est = len(rows) * (1800 * inp + 400 * out) / 1e6
        print(f"ESTIMATE: judging {len(rows)} drafts with {judge_model} ≈ ${est:.2f}. Re-run with --yes to proceed.")
        return
    judged = []
    for r in rows:
        scores, meta = judge(r, judge_model)
        judged.append({"claim_id": r["claim_id"], "predicted": r["predicted"], "planted_error": r["planted_error"],
                       "scores": scores, "cost_usd": meta["cost_usd"]})
        print(f"  {r['claim_id']} {r['predicted']:<12} acc={scores['accuracy']} ev={scores['evidence']} "
              f"cl={scores['clarity']} tone={scores['tone']}  {scores['justification'][:90]}")
    dims = ("accuracy", "evidence", "clarity", "tone")
    summary = {
        "split": split, "agent_model": agent_model, "judge_model": judge_model, "n_drafts": len(judged),
        **{f"mean_{d}": round(statistics.mean(j["scores"][d] for j in judged), 2) for d in dims},
        **{f"dist_{d}": {s: sum(1 for j in judged if j["scores"][d] == s) for s in range(1, 6)} for d in dims},
        "n_accuracy_below_4": sum(1 for j in judged if j["scores"]["accuracy"] < 4),
        "judge_total_cost_usd": round(sum(j["cost_usd"] for j in judged), 4),
        "human_sample": write_human_sheet(rows, split),
        "human_vs_judge_agreement": agreement(judged, split),
    }
    (ROOT / "results" / "judge_rubric.md").write_text(RUBRIC + "\n")
    out = ROOT / "results" / f"drafts_{split}_{agent_model}.json"
    out.write_text(json.dumps({"summary": summary, "drafts": judged}, indent=1, ensure_ascii=False))
    print("\nSUMMARY")
    print(json.dumps(summary, indent=1))
    print(f"written to {out.relative_to(ROOT)}; human sheet at results/human_scoring_sheet_{split}.md")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation", choices=["validation", "test"])
    ap.add_argument("--model", default=llm.DEFAULT_MODEL, help="the agent model whose drafts to judge")
    ap.add_argument("--judge", default=JUDGE_MODEL)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    main(a.split, a.model, a.judge, a.limit, a.yes)
