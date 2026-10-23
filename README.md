# Receipted

An AI agent that reads receipt and invoice images, checks them against a claim record, a price list and a policy document, flags problems with cited evidence, and drafts a reply to the submitter.

**Live demo:** https://receipted.streamlit.app · **Stack:** Python, Claude API (Haiku 5.5 / Opus 5.5), LangGraph, Chroma, Streamlit, pytest

![Receipted demo](docs/demo_screenshot.jpg)

## The problem

Finance teams, club treasurers and procurement staff check receipts and supplier bills by hand: does the claim match the receipt, do the numbers add up, is the price what we agreed, does it break a policy rule? It is slow, and mistakes slip through. Off-the-shelf tools read invoices well, but a team's own price list and policy are where the checking errors happen, and small teams don't pay for enterprise software.

A multimodal Claude model extracts line items and totals from the image. Plain Python then does the arithmetic checks, because code is exact and language models are not. Relevant policy clauses and price-list rows are retrieved from a local Chroma store, an LLM rule check must cite a clause and a receipt line for every issue it raises, and a verifier drops any issue whose evidence does not exist. The agent decides approve / needs_review / reject, sends unreadable documents to a human, and is measured on extraction accuracy, errors caught, false alarms, latency and cost.

## How it works

```mermaid
flowchart LR
    A[Receipt image + claim] --> B[extract<br/>multimodal LLM → JSON schema]
    B -->|unreadable or<br/>failed validation| F
    B --> C[maths_check<br/>Python arithmetic + claim matching]
    C --> D[retrieve<br/>Chroma: policy clauses + price rows]
    D --> E[rule_check<br/>LLM, must cite clause + receipt line]
    E --> V[verify<br/>Python drops issues without real evidence]
    V --> F[decide<br/>approve / needs_review / reject]
    F --> G[draft<br/>message to submitter]
```

- **Each job goes to the right tool.** The image model reads the messy photo. Plain Python does the arithmetic, because language models are unreliable at maths and code is exact. Chroma finds the policy clauses and price rows that matter. The rule-check model may raise an issue only if it cites a clause and a receipt line.
- **Every flag needs evidence.** The verifier, in plain Python, throws away any issue whose clause id does not exist in the policy, whose receipt line is not in the extraction, or whose price comparison does not hold when re-done in code. Dropped issues are counted and reported.
- **It knows when to pass to a human.** Unreadable images and failed extractions skip the checks and go straight to *needs review*. Medium-severity findings also go to a person; only high-severity findings with evidence produce a reject.
- **It is measured, not just demoed.** See the results below. Every number comes from a file in `results/` written by the scripts in `eval/`.

## How to run

```bash
git clone https://github.com/codedbygermaine/receipted && cd receipted
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pip install -e .
cp .env.example .env            # then put your ANTHROPIC_API_KEY in .env
.venv/bin/python data/prepare.py          # downloads CORD v2 (~2 GB) and writes data/images + data/gt
.venv/bin/python -m receipted.run --sample SAMPLE-002        # one claim, end to end
.venv/bin/streamlit run app/streamlit_app.py                 # the demo
.venv/bin/pytest                                             # 63 tests
```

Reproduce the evaluation (test split, prompts frozen; each script prints a cost estimate first):

```bash
.venv/bin/python eval/make_claims.py --split test
.venv/bin/python eval/eval_extraction.py --split test --model claude-haiku-5-5 --yes
.venv/bin/python eval/eval_extraction.py --split test --model claude-opus-5-5 --yes
.venv/bin/python eval/eval_checks.py --split test --yes
.venv/bin/python eval/eval_drafts.py --split test --yes
.venv/bin/python eval/report.py --split test
```

Every LLM response is cached on disk (keyed by input, prompt version and model), so re-runs are free.

<!-- RESULTS -->
## Results (test split)

### Extraction vs CORD ground truth

| model | receipts | item F1 | item precision | item recall | total correct | subtotal correct | tax correct | mean latency | mean cost / receipt |
|---|---|---|---|---|---|---|---|---|---|
| `claude-haiku-5-5` | 100 | 0.92 | 0.88 | 0.95 | 97% | 96% | 97% | 3.68s | $0.0006 |
| `claude-opus-5-5` | 100 | 0.92 | 0.88 | 0.95 | 97% | 98% | 100% | 4.13s | $0.0186 |

### Checks: full agent on 100 synthetic claims (`claude-haiku-5-5`)

| planted error | n | caught | recall |
|---|---|---|---|
| inflated amount | 10 | 10 | 100% |
| wrong quantity | 10 | 8 | 80% |
| item not on receipt | 10 | 10 | 100% |
| totals mismatch | 10 | 10 | 100% |
| policy breach | 10 | 9 | 90% |

| natural breach (from ground truth) | n | caught | recall |
|---|---|---|---|
| price above list | 3 | 3 | 100% |
| above 500k | 3 | 1 | 33% |
| packaging over 5000 | 2 | 0 | 0% |
| receipt inconsistent | 9 | 3 | 33% |

| metric | value |
|---|---|
| decision accuracy (approve / needs_review / reject) | 81% |
| clean claims (no planted error, no natural breach) | 41 |
| false alarms: clean claim flagged with an issue | 10 (24%) |
| clean claims held only because the receipt was hard to read | 5 |
| rule-check issues raised / dropped by verifier | 56 / 1 |
| mean cost per claim | $0.0013 |
| mean seconds per claim (uncached) | 6.22 |

### Drafts: LLM-as-judge (`claude-opus-5-5` scoring `claude-haiku-5-5` drafts, 1–5)

| accuracy | evidence | clarity | tone | drafts with accuracy < 4 |
|---|---|---|---|---|
| 4.55 | 4.9 | 4.71 | 4.95 | 5 / 100 |

_Human scoring sheet generated; agreement will be reported once it is filled in._

![errors caught per type](results/chart_recall_test.png)

![extraction by model](results/chart_models_test.png)
<!-- /RESULTS -->

The headline: **47 of 50 planted errors caught (94%)**, decision accuracy 81% on 100 claims, at about $0.0013 and 6 seconds per claim with Haiku 5.5. Drafts score 4.55 / 5 on accuracy and 4.9 / 5 on evidence from an Opus judge; the 5 weakest drafts all did a sum of their own in prose, which the maths check will phrase for them next time. The two models read receipts equally well; Haiku costs 30× less. The human-scoring sheet for 10 drafts is in `results/human_scoring_sheet_test.md`; agreement with the judge is reported once it is filled in.

## Error analysis

The five worst real failures, with image ids and causes, are in [results/error_analysis.md](results/error_analysis.md). In short:

1. **A false reject from a name with no spaces** (`SATE ATI GO` vs the printed `SATECATIGO`): the fuzzy matcher depends on token boundaries. Fix: compare with spaces stripped too.
2. **A price-list row matched to the wrong product** (a 230,000 cake vs `almond cream cheese`): the verifier checks that the row exists and the arithmetic holds, not that it is the same product. Largest source of false alarms. Fix: a name-similarity guard in the verifier.
3. **A missing purpose that went unflagged** on 1 of 10 claims: a model applies a rule most of the time, not every time. Fix: a one-line deterministic check.
4. **A missed tax line turned into a false alarm**: the human-review route caught it, at the cost of a reviewer's look.
5. **A wrong quantity caught only as "claim exceeds receipt"**: right decision, incomplete explanation, because the item's quantity or name did not match.

Reading the 10 flagged clean claims by hand, at least 3 are correct by the policy as written and were missed by the synthetic labels (a women's blouse under C6, a dinner above the per-person cap, `Teh Es` above the `es teh` row). The 24% false-alarm figure is therefore an upper bound; the genuinely wrong flags are closer to 4 or 5 of 41.

## Limitations

- **The claims, price list, policy and planted errors are synthetic.** Built by me, on top of real CORD images, and labelled as such throughout. The planted error types are the ones I thought of.
- **Indonesian receipts only.** CORD has no store name or date fields, so the deadline clause (C11) is not checked and duplicates cannot be detected.
- **Ground truth is imperfect.** Some CORD labels disagree with what the receipt prints (word order, zero-priced lines, "Sub Total" as total), so part of the measured extraction error is label noise.
- **One bug was fixed during the test run.** The claim-lines check mis-flagged clean claims whose items were listed before tax; found on the first 17 test claims, fixed, run restarted. The partial first run is kept in `results/checks_test_run1_partial.log`.
- **The judge is a model.** Opus scores Haiku's drafts against a rubric; the human-agreement number exists to check the judge.

## What I'd do next

1. Name-similarity guard in the verifier for price-list issues, and space-insensitive name matching (fixes failures 1 and 2 above).
2. Move "purpose is empty" and the two-approver threshold into deterministic checks; keep the LLM for judgements code can't make.
3. Route receipts Haiku marks "partly unclear" to Opus instead of a human, and measure how many reviews that saves.
4. Try the extraction prompt without zero-priced bundle lines, on the validation split first.
5. Expose `check_document(image, claim)` as an MCP tool, and test on Singapore receipts photographed by me.

## Use from Claude Desktop (MCP)

Receipted is also an MCP server, so Claude Desktop can call it as a tool. Add this to `claude_desktop_config.json` (Settings → Developer → Edit Config), with your own absolute paths, then restart Claude Desktop:

```json
{
  "mcpServers": {
    "receipted": {
      "command": "/Users/you/receipted/.venv/bin/python",
      "args": ["-m", "receipted.mcp_server"],
      "cwd": "/Users/you/receipted"
    }
  }
}
```

Then ask Claude something like *"Check /Users/you/receipt.jpg against a claim of 250,000 IDR for a committee dinner, 4 people, items: Sop Sui Jiao 1 × 33,000 …"* and it will call `check_document` and get back the decision, the verified issues with evidence and the draft message. To test the server without Claude Desktop:

```bash
.venv/bin/python scripts/mcp_client_test.py SAMPLE-002
```

## Attribution and licence

Receipt images and ground truth: **CORD v2** (`naver-clova-ix/cord-v2`, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)). Park, S. et al. "CORD: A Consolidated Receipt Dataset for Post-OCR Parsing", Document Intelligence Workshop at NeurIPS 2019. The five demo sample images in `app/samples/` are from the same dataset.

The claim records, price list, policy document and planted errors are **synthetic test fixtures** created for this project on top of the real CORD images, and are labelled as synthetic wherever they appear. Everything else in this repository is by Germaine Koh. Built with Claude Code.
