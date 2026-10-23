"""MCP server: lets Claude Desktop (or any MCP client) call Receipted as a tool.

Run over stdio:  .venv/bin/python -m receipted.mcp_server
The tool wraps run_claim() from graph.py and returns a compact result, leaving out the big
retrieval and trace blobs so the calling model gets a short, readable answer.
"""

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from receipted import llm
from receipted.graph import run_claim

server = MCPServer(
    name="receipted",
    instructions="Checks a receipt image against an expense claim, a price list and a policy. "
                 "Call check_document with the image path and the claim.",
)


@server.tool()
def check_document(
    image_path: str,
    amount: float,
    submitter: str = "member",
    purpose: str = "",
    items: list[dict[str, Any]] | None = None,
    claim_id: str = "MCP",
    currency: str = "IDR",
    model: str = llm.DEFAULT_MODEL,
) -> dict[str, Any]:
    """Check one receipt image against a claim. Returns the decision (approve / needs_review / reject),
    every verified issue with its evidence, how many issues the verifier dropped, and a draft message.
    items: list of {"name": str, "qty": number, "line_total": number} as claimed."""
    path = Path(image_path).expanduser()
    if not path.exists():
        return {"error": f"image not found: {path}"}

    def whole(v):  # JSON numbers arrive as floats; Rupiah has no cents
        return int(v) if isinstance(v, float) and v.is_integer() else v

    claim = {"claim_id": claim_id, "submitter": submitter, "purpose": purpose, "amount": whole(amount),
             "currency": currency,
             "items": [{**it, "qty": whole(it.get("qty", 1)), "line_total": whole(it.get("line_total"))} for it in items or []]}
    state = run_claim(path, claim, model=model, register=True)
    receipt = state.get("receipt")
    return {
        "decision": state["decision"],
        "decision_reason": state["decision_reason"],
        "receipt_total": receipt.get("total") if receipt else None,
        "readability": receipt.get("readability") if receipt else None,
        "verified_issues": [
            {k: i.get(k) for k in ("type", "severity", "message", "receipt_line", "clause_id", "price_item", "evidence")}
            for i in state["verified_issues"]
        ],
        "dropped_by_verifier": len(state["dropped_issues"]),
        "draft": state["draft"],
        "total_cost_usd": state["total_cost_usd"],
        "total_seconds": state["total_seconds"],
        "model": state["model"],
    }


if __name__ == "__main__":
    server.run(transport="stdio")
