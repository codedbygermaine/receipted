# Reviewer pilot

Everything measured so far says the checks are right on test claims. This pilot asks the other question: does
Receipted help a person who approves expenses make correct decisions faster, and do they trust its holds?

## Who and what

- **Two volunteer approvers** (a third withdrew), each with some experience of checking claims (club treasurer,
  committee finance, or a finance role). They are not told which claims contain problems.
- **Twenty claims**, drawn from the Singapore receipt set with claims written for the pilot: about half clean, the
  rest with one problem each (amount above the receipt, a personal item, a meal over the per-person limit, a
  missing purpose, a duplicate). The answer key is fixed before the first session and not shown to anyone.
- **Two conditions**, counterbalanced: each approver clears ten claims **with Receipted** (the approvals inbox)
  and ten **by hand** (receipt photo, claim details and the written policy, nothing else). One approver
  starts with the tool and the other without, and the claim sets swap, so no claim is always in the same condition.

## What is measured, per claim

| Measure | How |
|---|---|
| Time to decision | Stopwatch from opening the claim to pressing approve / reject / ask (tool) or writing the decision (by hand). The API stores the decision time; the open time is noted by the observer. |
| Correct decision | Compared with the answer key: approve, reject, or hold-with-a-question. |
| Unnecessary review | A clean claim the approver held or questioned. |
| Override | A claim where the approver's decision differed from the tool's. The approver says why, in one sentence, recorded verbatim. |
| Trust | After the session, three questions scored 1 to 5: Did you understand why each claim was held? Did the flags point at the right line? Would you use this for your own claims? |

## Recording and writing up

Fill `results/pilot_sheet.csv` during the sessions, one row per claim (the columns are explained at the top of
`eval/pilot_summary.py`). Then run `.venv/bin/python eval/pilot_summary.py` and paste its output under a
"Reviewer pilot" heading in `docs/evaluation.md`, with one paragraph on what the approvers said.

## What gets published

In `docs/evaluation.md`, under a "Reviewer pilot" heading: minutes per correct decision with and without the
tool, unnecessary reviews in each condition, the number of overrides with their reasons, and the trust scores,
for both approvers, with the small sample stated plainly. Two people and twenty claims is a pilot, not a
validation, and the write-up says so.

## How to describe it before the results exist

Once the first session has happened: "A pilot with two volunteer approvers is under way; results will be
published in the evaluation." Not before. Nothing about the pilot goes on the landing page or in the case
study until the numbers are in.
