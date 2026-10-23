"""Shared bits for every LLM call: the client, model names, prices, and the disk cache.

Why a cache: every call costs money and takes seconds. Keyed by (content, prompt version, model),
a re-run of the same input is free and instant, and results are reproducible.
"""

import hashlib
import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DEFAULT_MODEL = "claude-haiku-5-5"
LARGE_MODEL = "claude-opus-5-5"

# USD per million tokens (input, output). From platform.claude.com pricing, Oct 2026.
PRICES_PER_MTOK = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}

# Everything the system writes goes under DATA_DIR. On a laptop that is the repo's data/ folder; on a
# read-only runtime such as AWS Lambda, set RECEIPTED_DATA_DIR=/tmp.
DATA_DIR = Path(os.environ.get("RECEIPTED_DATA_DIR", ROOT / "data"))
CACHE_DIR = DATA_DIR / "cache"

_client = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    inp, out = PRICES_PER_MTOK[model]
    return (input_tokens * inp + output_tokens * out) / 1_000_000


def cache_key(*parts) -> str:
    """Stable hash of everything that could change the answer."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else str(p).encode())
        h.update(b"\x00")
    return h.hexdigest()[:24]


def cache_get(kind: str, key: str) -> dict | None:
    path = CACHE_DIR / kind / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def cache_put(kind: str, key: str, value: dict) -> None:
    path = CACHE_DIR / kind / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False))
