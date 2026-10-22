# Receipted — project context for Claude Code

## Who I am and how to work with me
- I'm Germaine, a Year 2 NTU Economics & Data Science student. I'm comfortable reading Python but I'm not a heavy coder.
- I must be able to explain EVERY part of this project in an interview with no AI tools allowed. So:
  - Before writing code for a phase, explain the plan in plain English in 5–8 lines.
  - After each phase, add a short section to LEARNING.md: what we built, why it's designed that way,
    1–2 likely interview questions with answers, and any trade-off we chose.
  - Keep code simple and readable. Prefer clear functions over clever abstractions. Add short comments on the "why".
- Work in small steps. Run things and show me real output. Don't write large amounts of untested code.

## Honesty rules (non-negotiable)
- Never invent results. Every number in README.md must come from a file in results/ produced by eval scripts.
- If a metric is bad, report it honestly and add an error analysis. Do not tune on the test split.
- Label all synthetic data (claims, price list, policy, planted errors) as synthetic in the README.
- Credit the CORD dataset (CC BY 4.0) in the README.

## What we're building
An agent that checks a receipt/invoice image against a claim record, a price list and a policy:
extract line items (multimodal LLM) → deterministic maths checks (Python) → retrieve relevant policy clauses
and price-list entries (RAG, Chroma) → rule checks that must cite evidence → evidence verifier drops
unsupported issues → decision (approve / needs_review / reject) → draft message to submitter.
Then evaluate it properly and ship a Streamlit demo.

## Stack
- Python 3.11+, uv or venv, `.env` + python-dotenv for ANTHROPIC_API_KEY (never commit it)
- Anthropic Python SDK (Claude with image input). Check docs.anthropic.com for CURRENT model IDs. Do not
  guess model names. Use a small/fast Claude model as default and a larger one for comparison.
- Structured output: use tool use / JSON schema with Pydantic validation. Retry once on invalid JSON.
- LangGraph for the agent graph (check the current LangGraph docs for the current API before writing it)
- Chroma (local, persistent) for retrieval over policy.md and price_list.csv
- Streamlit for the demo; pytest for tests
- Data: Hugging Face `naver-clova-ix/cord-v2` (ground_truth is a JSON string with key "gt_parse":
  menu[{nm, cnt, unitprice, price}], sub_total{...}, total{total_price, ...}). Prices are strings
  like "75,000" (Indonesian Rupiah, comma thousands separators) — normalise them carefully.

## Cost and safety
- Before any batch run over more than 10 images, print estimated API calls and cost and wait for my OK.
- Cache every LLM response to disk (keyed by image id + prompt version + model) so re-runs are free.
- Use the CORD validation split for development and prompt tweaks; use the test split ONLY for final numbers.

## Repo layout
receipted/
  CLAUDE.md, README.md, LEARNING.md, requirements.txt, .env.example, .gitignore
  data/ (downloaded + generated; large files gitignored)
  fixtures/policy.md, fixtures/price_list.csv
  src/receipted/{schemas.py, extract.py, maths.py, retrieve.py, rules.py, verify.py, graph.py, draft.py}
  eval/{make_claims.py, eval_extraction.py, eval_checks.py, eval_drafts.py, report.py}
  results/ (metrics json/csv + charts, committed)
  app/streamlit_app.py
  tests/
