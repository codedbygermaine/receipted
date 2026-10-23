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

CHROMA_PATH = ROOT / "chroma_db"

# One policy and price list per currency. A receipt's currency picks the set; unknown currencies use IDR,
# the set the project was built and measured on.
POLICY_SETS = {
    "IDR": {"policy": ROOT / "fixtures" / "policy.md", "prices": ROOT / "fixtures" / "price_list.csv"},
    "SGD": {"policy": ROOT / "fixtures" / "policy_sgd.md", "prices": ROOT / "fixtures" / "price_list_sgd.csv"},
}
DEFAULT_CURRENCY = "IDR"


def policy_set_for(currency: str | None) -> str:
    return (currency or DEFAULT_CURRENCY).upper() if (currency or "").upper() in POLICY_SETS else DEFAULT_CURRENCY

POLICY_PATH = POLICY_SETS["IDR"]["policy"]
PRICE_PATH = POLICY_SETS["IDR"]["prices"]

CLAUSE_RE = re.compile(r"^### (C\d+)\. (.+?)\n(.*?)(?=^### |\Z)", re.M | re.S)


def load_policy_clauses(currency: str | None = None) -> dict[str, dict]:
    """{'C3': {'id': 'C3', 'title': 'Alcohol and tobacco', 'text': '...'}, ...} for the currency's policy set."""
    text = POLICY_SETS[policy_set_for(currency)]["policy"].read_text()
    return {m.group(1): {"id": m.group(1), "title": m.group(2).strip(), "text": m.group(3).strip()}
            for m in CLAUSE_RE.finditer(text)}


def load_price_list(currency: str | None = None) -> dict[str, dict]:
    """{'nasi putih': {'item': 'nasi putih', 'agreed_max_unit_price': 11000, ...}, ...} for the currency's set."""
    with open(POLICY_SETS[policy_set_for(currency)]["prices"], newline="") as f:
        lines = [line for line in f if not line.startswith("#")]
    rows = {}
    for r in csv.DictReader(lines):
        rows[r["item"]] = {"item": r["item"],
                           "agreed_max_unit_price": float(r["agreed_max_unit_price"]),
                           "typical_price_seen": float(r["typical_price_seen"])}
    return rows


_collections: dict[str, tuple] = {}


def collections(rebuild: bool = False, currency: str | None = None):
    """Open (and if needed build) the two Chroma collections for a currency's policy set. Cached per process."""
    cur = policy_set_for(currency)
    if cur in _collections and not rebuild:
        return _collections[cur]
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    clauses, prices = load_policy_clauses(cur), load_price_list(cur)
    suffix = "" if cur == DEFAULT_CURRENCY else f"_{cur.lower()}"

    def fresh(name, ids, documents, metadatas):
        existing = [c.name for c in client.list_collections()]
        col = client.get_collection(name) if name in existing else None
        if rebuild or col is None or col.count() != len(ids):
            if col is not None:
                client.delete_collection(name)
            col = client.create_collection(name)
            col.add(ids=ids, documents=documents, metadatas=metadatas)
        return col

    policy = fresh("policy_clauses" + suffix, list(clauses),
                   [f"{c['title']}. {c['text']}" for c in clauses.values()],
                   [{"title": c["title"]} for c in clauses.values()])
    price = fresh("price_list" + suffix, list(prices), list(prices),
                  [{"agreed_max_unit_price": r["agreed_max_unit_price"]} for r in prices.values()])
    _collections[cur] = (policy, price, clauses, prices)
    return _collections[cur]


def retrieve_policy(query: str, k: int = 4, currency: str | None = None) -> list[dict]:
    policy, _, clauses, _ = collections(currency=currency)
    res = policy.query(query_texts=[query], n_results=min(k, policy.count()))
    return [{**clauses[cid], "distance": round(d, 3)} for cid, d in zip(res["ids"][0], res["distances"][0])]


def retrieve_prices(item_name: str, k: int = 3, currency: str | None = None) -> list[dict]:
    _, price, _, prices = collections(currency=currency)
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
    cur = receipt.get("currency")
    add(retrieve_policy(claim_text, k_policy_claim, currency=cur))
    price_hits = {}
    for it in receipt["items"]:
        if it["name"]:
            add(retrieve_policy(it["name"], k_policy_per_item, currency=cur))
            price_hits[it["name"]] = retrieve_prices(it["name"], 3, currency=cur)
    return {"clauses": clause_hits, "price_rows": price_hits, "policy_set": policy_set_for(cur)}
