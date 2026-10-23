"""Spawn the MCP server over stdio exactly as Claude Desktop would, list its tools, and call
check_document on a sample claim. Usage: .venv/bin/python scripts/mcp_client_test.py [SAMPLE-002]"""

import asyncio
import json
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]
sample_id = sys.argv[1] if len(sys.argv) > 1 else "SAMPLE-002"


async def main():
    claims = {c["claim_id"]: c for c in json.load(open(ROOT / "fixtures" / "sample_claims.json"))}
    claim = claims[sample_id]
    gt = {r["id"]: r for s in ("validation", "test") for r in json.load(open(ROOT / "data" / "gt" / f"{s}.json"))}
    image = str(ROOT / gt[claim["receipt_id"]]["image_path"])

    params = StdioServerParameters(command=str(ROOT / ".venv" / "bin" / "python"),
                                   args=["-m", "receipted.mcp_server"], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            result = await session.call_tool("check_document", {
                "image_path": image, "amount": claim["amount"], "submitter": claim["submitter"],
                "purpose": claim["purpose"], "items": claim["items"], "claim_id": claim["claim_id"],
            })
            payload = result.structured_content or json.loads(result.content[0].text)
            print(json.dumps(payload, indent=1, ensure_ascii=False))


asyncio.run(main())
