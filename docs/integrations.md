# Using Receipted: web demo, HTTP API, MCP

Three ways in, all on the same checker.

## The web demo

The web demo at https://codedbygermaine.github.io/receipted/ is a small React app (`web/`: Vite, Tailwind and shadcn/ui, published by GitHub Pages) that talks to this API. It has two sides: a claimant picks or uploads a receipt, fills in the claim and gets a verdict where every issue points at a receipt line and a policy clause; an approver sees the held claims in an inbox with the receipt and the evidence, and their approve/reject writes the reply. The page carries a separate demo token with its own small daily cap, so anyone can try it and the worst a stranger can do is use up a day of demo budget. API Gateway caps a request at 30 s, so a check runs as a background job: `POST /check` returns 202 and a job id, the page polls `GET /jobs/{id}`, and results live in S3 for seven days.

## HTTP API on AWS Lambda

Besides `POST /check` and `GET /jobs/{id}`, the approval flow uses `GET /inbox` (held claims, newest per receipt image), `GET /jobs/{id}/image`, `POST /jobs/{id}/ask` (the approver's question, kept as a thread on the claim), `POST /jobs/{id}/answer` (the claimant's reply, which puts the claim back in the queue) and `POST /jobs/{id}/decide` (approve or reject, which rewrites the reply and includes the claimant's answer).

The same checker as a web endpoint, for anything that can send an HTTP request (a club's web form, a spreadsheet macro, another service). `api/app.py` is a FastAPI app; on AWS it runs as a Lambda container image behind API Gateway in the Singapore region, pay-per-request. Live at `https://72dxv5aw0m.execute-api.ap-southeast-1.amazonaws.com` (health check is open; checks need the token). Every call needs the token in `X-Api-Token`, and a daily cap stops a public URL from running up the bill.

```bash
curl -s -X POST "$URL/check" -H "X-Api-Token: $TOKEN" \
  -F image=@receipt.jpg \
  -F 'claim={"claim_id":"C-1","submitter":"A. Member","purpose":"Team lunch, 3 people","amount":101.90}'
```

The reply is JSON: decision, reason, currency, receipt total, extracted items with confidence, every verified issue with its evidence, the draft message, cost and time. Deploying is one script once the AWS CLI is signed in and Docker is running:

```bash
RECEIPTED_API_TOKEN=choose-a-token ANTHROPIC_API_KEY=sk-ant-... ./api/deploy.sh
```

It builds the image (policy index and embedding model baked in, so cold starts download nothing), pushes it to ECR, creates or updates the Lambda and its API Gateway in the Singapore region, and prints the URL. Run locally with `RECEIPTED_API_TOKEN=dev uvicorn api.app:app`.

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
