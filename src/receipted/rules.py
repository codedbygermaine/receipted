"""The LLM rule check: given the facts (extracted receipt, claim, maths results) and the retrieved
policy clauses and price rows, decide which rules are broken. Every issue must cite a clause or
price row AND the receipt line it applies to, so the verifier can check it.
"""

import json
import time
from typing import Literal

from pydantic import BaseModel, Field

from receipted import llm

PROMPT_VERSION = "v3"

ANCHORS = ("RECEIPT_TOTAL", "CLAIM_AMOUNT")  # allowed receipt_line values for whole-claim rules


class RuleIssue(BaseModel):
    type: str = Field(description="Short snake_case label, e.g. alcohol_item, price_above_list, needs_two_approvers")
    severity: Literal["low", "medium", "high"]
    clause_id: str | None = Field(description="Policy clause id exactly as given, e.g. C3. null if the issue is only about the price list")
    price_item: str | None = Field(description="Price-list item name exactly as given, or null")
    receipt_line: str = Field(description="The receipt line copied exactly, or RECEIPT_TOTAL / CLAIM_AMOUNT for whole-claim rules")
    explanation: str = Field(description="One or two sentences a treasurer could act on")


class RuleIssues(BaseModel):
    issues: list[RuleIssue]


SYSTEM_PROMPT = """You check expense claims for a club treasurer. You are given facts that code has already established
(the extracted receipt lines, the claim, and arithmetic problems already found) plus the policy clauses and
price-list rows that retrieval judged relevant.

Raise an issue ONLY when a given clause or price row clearly applies to a specific receipt line or to the claim.
- clause_id must be one of the clause ids shown. price_item must be one of the price-list item names shown.
- receipt_line must be copied character for character from the RECEIPT LINES, or be RECEIPT_TOTAL / CLAIM_AMOUNT
  when the rule is about the whole claim (e.g. approval thresholds).
- Prices on the receipt are unit prices only when a unit price column is printed; otherwise compare line_total / qty.
- Do not restate the arithmetic issues already listed; they are recorded. You may add a policy issue that follows from one.
- Also check the claim itself against the clauses: its stated purpose (or lack of one), the number of people for a meal,
  and the claimed amount against any approval threshold. Cite CLAIM_AMOUNT as the line for those.
- severity follows the clause wording: "high" when the clause says the claim or item is rejected or never
  reimbursable; "medium" when it says the claim is held for review or needs approval; "low" for anything softer.
- If nothing applies, return an empty list. Never invent clauses, prices or lines."""


def _format_facts(receipt: dict, claim: dict, maths_issues: list[dict], retrieved: dict) -> str:
    lines = []
    purpose = (claim.get("purpose") or "").strip()
    lines.append(f"CLAIM PURPOSE: {purpose if purpose else '(not stated)'}")
    lines.append("CLAIM:\n" + json.dumps(claim, ensure_ascii=False, indent=1))
    lines.append("RECEIPT LINES (copy raw_line exactly when citing):")
    for it in receipt["items"]:
        lines.append(f'- raw_line: "{it["raw_line"]}" | name: {it["name"]} | qty: {it["qty"]} | '
                     f'unit_price: {it["unit_price"]} | line_total: {it["line_total"]}')
    lines.append(f"RECEIPT TOTALS: subtotal={receipt['subtotal']} tax={receipt['tax']} service={receipt['service']} "
                 f"discount={receipt['discount']} total={receipt['total']} currency={receipt['currency']} "
                 f"readability={receipt['readability']}")
    lines.append("ARITHMETIC ISSUES ALREADY FOUND BY CODE:")
    lines += [f"- {m['type']} ({m['severity']}): {m['message']}" for m in maths_issues] or ["- none"]
    lines.append("POLICY CLAUSES (retrieved):")
    lines += [f"- {c['id']}. {c['title']}: {c['text']}" for c in retrieved["clauses"]]
    lines.append("PRICE LIST ROWS (retrieved per receipt item; agreed_max_unit_price in IDR):")
    for name, rows in retrieved["price_rows"].items():
        lines.append(f"- for receipt item '{name}': " +
                     "; ".join(f"'{r['item']}' max {r['agreed_max_unit_price']}" for r in rows))
    return "\n".join(lines)


def check_rules(receipt: dict, claim: dict, maths_issues: list[dict], retrieved: dict,
                model: str = llm.DEFAULT_MODEL) -> tuple[list[dict], dict]:
    """Returns (issues, meta). meta has tokens, latency, cost and whether it was cached."""
    facts = _format_facts(receipt, claim, maths_issues, retrieved)
    key = llm.cache_key(facts, PROMPT_VERSION, model, SYSTEM_PROMPT)
    hit = llm.cache_get("rules", key)
    if hit:
        return hit["issues"], {**hit["meta"], "cached": True}

    start = time.perf_counter()
    response = llm.client().messages.parse(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": facts}],
        output_format=RuleIssues,
        output_config={"effort": "medium"},
    )
    parsed = response.parsed_output
    raw = parsed.issues if parsed is not None else []
    issues = [{
        "source": "rules",
        "type": r.type,
        "severity": r.severity,
        "message": r.explanation,
        "receipt_line": r.receipt_line,
        "clause_id": r.clause_id,
        "price_item": r.price_item,
        "evidence": {},
    } for r in raw]
    meta = {
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_s": round(time.perf_counter() - start, 2),
        "cost_usd": round(llm.cost_usd(model, response.usage.input_tokens, response.usage.output_tokens), 6),
        "stop_reason": response.stop_reason,
        "cached": False,
    }
    llm.cache_put("rules", key, {"issues": issues, "meta": meta})
    return issues, meta
