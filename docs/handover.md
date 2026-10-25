# Receipted: handover brief

Written 25 October 2026 so that another assistant (or a future me) can pick the project up with full context.
Everything below is current as of the last commit on `main`.

## What Receipted is

An AI expense reviewer that shows its working. A claimant uploads a receipt photo, enters the amount and the
purpose. Receipted reads the receipt (Claude Haiku 5.5, image input), does every piece of arithmetic in plain
Python, retrieves the relevant policy clauses and agreed prices (Chroma), asks a model whether a specific line
breaks a specific rule (it must cite the line and the clause), drops any flag whose evidence doesn't hold, decides
approve / needs review / reject, and writes the reply. Claims that need review wait in an approvals inbox where an
approver sees the receipt beside the flagged lines and can approve, reject, or ask the claimant a question. The
claimant is emailed when the claim is checked, questioned and decided, if they gave an address.

Positioning: business-neutral. Words used: claimant, approver, Finance, expense policy. The student club it was
built for is only the origin story in the case study.

## Where everything is

| Thing | Where |
|---|---|
| Live site | https://codedbygermaine.github.io/receipted/ (GitHub Pages, built from `web/` by `.github/workflows/pages.yml` on every push to `main`) |
| API | `https://72dxv5aw0m.execute-api.ap-southeast-1.amazonaws.com` (FastAPI on AWS Lambda container, API Gateway, S3 bucket `receipted-api-jobs-411334288019` for jobs, 7-day lifecycle). Code in `api/app.py`, image in `api/Dockerfile`, deploy with `set -a; . ./.env; set +a; ./api/deploy.sh` from the repo root (use absolute paths; the script needs `.env` exported) |
| Repo | https://github.com/codedbygermaine/receipted. `src/receipted/` pipeline, `eval/` evaluation scripts, `results/` every number the docs quote, `web/` React + Vite + Tailwind + shadcn/ui front end, `docs/` evaluation, case study, production practices, integrations, pilot protocol, `LEARNING.md` phase-by-phase log, `tests/` 87 pytest tests, CI runs tests and a regression gate |
| Tokens | `.env` (never committed): `ANTHROPIC_API_KEY`, `RECEIPTED_API_TOKEN` (full tier), `RECEIPTED_DEMO_TOKEN` (public, embedded in `web/public/config.js`, 40 checks a day, never registers duplicates), `RECEIPTED_EMAIL_FROM` |
| Front end dev | `cd web && npm run dev` then open `http://localhost:5173/receipted/`; `npm run build` must pass before pushing |

## The numbers (test split, 100 real CORD receipts, 100 claims written by Germaine, 50 with a planted error)

48 of 50 planted errors caught (Wilson 95% CI 87–99%); decision accuracy 83% (74–89%); clean claims flagged
8 of 41 (an upper bound: at least 3 are real breaches the labels missed); receipt totals read correctly 97%; item
F1 0.92; 0 fabricated digits when the total was masked on 98 receipts; $0.0013 model cost and about 5 s per claim;
the larger model caught no more errors at 30× the cost. Both test runs are published (run 1 before fixes, run 2
after). Every number comes from a script in `eval/` writing to `results/`; `results/results_table.md` is injected
into `docs/evaluation.md`. Never quote a number that isn't in `results/`.

## Rules Germaine has set (do not break)

- Never the middle dot "·" anywhere in the UI.
- Minimal words: no explanatory sentences, hints, counters, diagnostics or disclaimers on product screens. Grey
  scale plus one dark accent, colour only for meaning, no badges, no cards inside cards, nothing that looks
  AI-generated.
- Never invent names: sample claims don't prefill a claimant name.
- Never the word "synthetic": say "written for testing".
- The four clinic receipts stay out of the repo; card numbers are masked in code.
- Honesty: report bad results, disclose changes made after the test run, say "pilot under way" only once the
  first session has happened.

## How the demo behaves (deliberate decisions)

- Six sample receipts, all Germaine's own Singapore receipts, with sample claims filled in: team brunch
  (approve), notebook (approve), client lunch for two (held, over SGD 40 a person), pharmacy run (held, medicines
  need a business purpose), event outfit (rejected, clothing), team lunch over-claimed (rejected).
- One verified reading of each sample receipt is pinned into the API image (`api/cache_seed`) so every visitor
  gets the same extraction. Uploaded receipts are read fresh.
- The approvals queue shows the newest claim per receipt image and is shared by all visitors (demo token).
- Two restaurant receipts (sg_06, sg_20) are not used as samples: priced add-ons get double-counted by the
  extractor and trip the arithmetic check.
- The two-approver rule (C7) and the personal-items screen (C6) are deterministic code, not model judgement.

## Open items

1. **Email delivery to strangers.** Amazon SES is in sandbox: only verified addresses receive mail. Germaine's
   address and two pilot volunteers' addresses are verified (or pending their click). AWS denied production
   access (case 179291608400851); appeal in the AWS Support Center, or switch to another transactional provider.
   The site already tells a claimant honestly when an address can't be reached.
2. **Spam placement.** Mail is sent from a gmail.com address via SES, so Gmail distrusts it. The fix is a domain
   Germaine controls, verified in SES; deferred for now.
3. **Reviewer pilot.** Protocol in `docs/pilot.md`, two volunteers. Results go in `docs/evaluation.md`.
4. **Old Streamlit app** at receipted.streamlit.app is unmaintained and nothing links to it; delete it in
   Streamlit Cloud.
5. Known model quirk: one reply once said "claym"; recorded in `results/error_analysis.md`, not patched.

## Known traps when working on it

- Background shell commands may start in `web/`; use absolute paths for `.venv/bin/python`, `.env` and
  `api/deploy.sh`, and check the Lambda's LastModified after a deploy.
- A deploy that didn't actually run looks successful if you only read the log tail.
- The cache on Lambda lives in `/tmp` per container; anything that must be identical across visitors has to be
  baked into the image.
- Changing prompts invalidates cached model outputs and the measured numbers; don't touch `fixtures/policy.md`
  (the Indonesian policy the test numbers were measured on) or the extraction and rule prompts without re-running
  and disclosing.
