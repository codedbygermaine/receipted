"""Write the message to the submitter. The model only gets verified issues, so it can only mention
problems that have evidence. It is told to merge overlapping findings and add nothing new.
"""

import json
import time

from receipted import llm

PROMPT_VERSION = "v2"   # v2: written from a finance approver, signed "Finance" (was: club treasurer)

SYSTEM_PROMPT = """You write short, polite messages from the finance approver to a colleague about their expense claim.
Sign off as "Finance".
Rules:
- Mention ONLY the issues given. Do not add, soften or invent facts. Quote the numbers and clause ids given.
- Two issues may describe the same problem (one found by arithmetic, one by policy). Present each distinct problem once,
  giving the numbers and the clause id together.
- Keep it under 150 words. Plain language, no bullet symbols other than "-". No greeting longer than one line.
- Decision wording: approve -> say it is approved and will be paid; needs_review -> say it is on hold and what the
  claimant can do; reject -> say it cannot be paid as submitted and what would fix it."""


def write_draft(claim: dict, receipt: dict | None, decision: str, reason: str, issues: list[dict],
                model: str = llm.DEFAULT_MODEL) -> tuple[str, dict]:
    facts = {
        "claim_id": claim.get("claim_id"),
        "submitter": claim.get("submitter", "member"),
        "claimed_amount": claim.get("amount"),
        "currency": claim.get("currency") or (receipt or {}).get("currency") or "IDR",
        "receipt_total": receipt.get("total") if receipt else None,
        "decision": decision,
        "decision_reason": reason,
        "issues": [{"type": i["type"], "severity": i["severity"], "message": i["message"],
                    "receipt_line": i.get("receipt_line"), "clause_id": i.get("clause_id"),
                    "evidence": i.get("evidence", {})} for i in issues],
    }
    text = json.dumps(facts, ensure_ascii=False, indent=1)
    key = llm.cache_key(text, PROMPT_VERSION, model, SYSTEM_PROMPT)
    hit = llm.cache_get("draft", key)
    if hit:
        return hit["draft"], {**hit["meta"], "cached": True}

    start = time.perf_counter()
    response = llm.client().messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": "Write the message for this claim:\n" + text}],
        output_config={"effort": "low"},
    )
    draft = "".join(b.text for b in response.content if b.type == "text").strip()
    meta = {
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_s": round(time.perf_counter() - start, 2),
        "cost_usd": round(llm.cost_usd(model, response.usage.input_tokens, response.usage.output_tokens), 6),
        "cached": False,
    }
    llm.cache_put("draft", key, {"draft": draft, "meta": meta})
    return draft, meta
