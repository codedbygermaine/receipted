"""Retrieval (the R in RAG): find the policy clauses and price-list rows relevant to a receipt.

The policy and price list are embedded once into a local Chroma store. For each receipt item we
ask Chroma for the nearest clauses and price rows, and hand only those to the LLM rule check.
With 13 clauses we could paste the whole policy into the prompt; retrieval is built the way it
would need to be for a 40-page policy, and it also gives the verifier an allowlist of real IDs.
"""

import csv
import re

import chromadb

from receipted.llm import ROOT

POLICY_PATH = ROOT / "fixtures" / "policy.md"
PRICE_PATH = ROOT / "fixtures" / "price_list.csv"
CHROMA_PATH = ROOT / "chroma_db"

CLAUSE_RE = re.compile(r"^### (C\d+)\. (.+?)\n(.*?)(?=^### |\Z)", re.M | re.S)


def load_policy_clauses() -> dict[str, dict]:
    """{'C3': {'id': 'C3', 'title': 'Alcohol and tobacco', 'text': '...'}, ...}"""
    text = POLICY_PATH.read_text()
    return {m.group(1): {"id": m.group(1), "title": m.group(2).strip(), "text": m.group(3).strip()}
            for m in CLAUSE_RE.finditer(text)}


def load_price_list() -> dict[str, dict]:
    """{'nasi putih': {'item': 'nasi putih', 'agreed_max_unit_price': 11000, ...}, ...}"""
    with open(PRICE_PATH, newline="") as f:
        lines = [line for line in f if not line.startswith("#")]
    rows = {}
    for r in csv.DictReader(lines):
        rows[r["item"]] = {"item": r["item"],
                           "agreed_max_unit_price": int(r["agreed_max_unit_price"]),
                           "typical_price_seen": int(r["typical_price_seen"])}
    return rows


_collections = None


def collections(rebuild: bool = False):
    """Open (and if needed build) the two Chroma collections. Cached per process."""
    global _collections
    if _collections is not None and not rebuild:
        return _collections
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    clauses, prices = load_policy_clauses(), load_price_list()

    def fresh(name, ids, documents, metadatas):
        existing = [c.name for c in client.list_collections()]
        col = client.get_collection(name) if name in existing else None
        if rebuild or col is None or col.count() != len(ids):
            if col is not None:
                client.delete_collection(name)
            col = client.create_collection(name)
            col.add(ids=ids, documents=documents, metadatas=metadatas)
        return col

    policy = fresh("policy_clauses", list(clauses),
                   [f"{c['title']}. {c['text']}" for c in clauses.values()],
                   [{"title": c["title"]} for c in clauses.values()])
    price = fresh("price_list", list(prices), list(prices),
                  [{"agreed_max_unit_price": r["agreed_max_unit_price"]} for r in prices.values()])
    _collections = (policy, price, clauses, prices)
    return _collections


def retrieve_policy(query: str, k: int = 4) -> list[dict]:
    policy, _, clauses, _ = collections()
    res = policy.query(query_texts=[query], n_results=min(k, policy.count()))
    return [{**clauses[cid], "distance": round(d, 3)} for cid, d in zip(res["ids"][0], res["distances"][0])]


def retrieve_prices(item_name: str, k: int = 3) -> list[dict]:
    _, price, _, prices = collections()
    res = price.query(query_texts=[item_name], n_results=min(k, price.count()))
    return [{**prices[pid], "distance": round(d, 3)} for pid, d in zip(res["ids"][0], res["distances"][0])]


def retrieve_for(receipt: dict, claim: dict, k_policy_per_item: int = 2, k_policy_claim: int = 5) -> dict:
    """Everything the rule check needs: clauses relevant to the items and the claim, price rows per item."""
    seen, clause_hits = set(), []

    def add(hits):
        for h in hits:
            if h["id"] not in seen:
                seen.add(h["id"])
                clause_hits.append(h)

    purpose = (claim.get("purpose") or "").strip() or "NOT STATED (purpose missing)"
    claim_text = f"expense claim, purpose: {purpose}. amount {claim.get('amount')}. items: " + \
                 ", ".join(ci["name"] for ci in claim.get("items") or [])
    add(retrieve_policy(claim_text, k_policy_claim))
    price_hits = {}
    for it in receipt["items"]:
        if it["name"]:
            add(retrieve_policy(it["name"], k_policy_per_item))
            price_hits[it["name"]] = retrieve_prices(it["name"], 3)
    return {"clauses": clause_hits, "price_rows": price_hits}
