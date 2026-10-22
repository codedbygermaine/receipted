# LEARNING.md — what we built and why, phase by phase

## Phase 0: Setup

**What we built.** Folder layout, a virtual environment, `requirements.txt`, `.env.example`, `.gitignore`, a README with the CORD attribution, and `scripts/hello.py` which proves the API key works.

**Why it's designed this way.**
- The API key lives only in `.env`, which `.gitignore` blocks. Code reads it with `python-dotenv` and the Anthropic client picks it up from the environment, so the key never appears in source.
- `.env.example` is committed instead, so anyone cloning knows which variable to set.
- Default model is Claude Haiku 5.5 (`claude-haiku-5-5`): cheapest current model, supports images, so the full test set costs cents. Claude Opus 5.5 (`claude-opus-5-5`) is the larger model for the comparison in Phase 5.
- The hello script lists models from the API rather than hardcoding knowledge, so model IDs are checked against the account, not guessed.

**Likely interview questions.**
- *Why not just paste the key into the script?* Anything in a public repo is public forever, even if deleted later. Secrets go in environment variables; `.env` is a local convenience for that.
- *Why a small model by default?* Most of the pipeline's hard logic is in plain Python. The LLM only needs to read the image well, and we measure whether a small model is good enough before paying for a larger one.

**Trade-off.** Python 3.13 is installed rather than the 3.11/3.12 the brief suggests. All pinned libraries install on 3.13; if one breaks later we can switch the venv to 3.12.
