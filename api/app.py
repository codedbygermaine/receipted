"""HTTP API for Receipted: POST a receipt image and a claim, get the decision, issues, evidence and draft.

Runs anywhere FastAPI runs; on AWS Lambda it is wrapped by Mangum (see Dockerfile). Every request needs
the token in X-Api-Token, and the daily cap stops a public URL from running up the bill.

Local:  RECEIPTED_API_TOKEN=dev .venv/bin/uvicorn api.app:app --port 8000
        curl -F image=@app/samples/validation_000.jpg -F 'claim={"claim_id":"T1","amount":45500,"purpose":"snacks"}' \\
             -H "X-Api-Token: dev" http://localhost:8000/check
"""

import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from mangum import Mangum

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from receipted import llm                     # noqa: E402
from receipted.graph import run_claim         # noqa: E402

API_TOKEN = os.environ.get("RECEIPTED_API_TOKEN", "")
DAILY_CAP = int(os.environ.get("RECEIPTED_DAILY_CAP", "100"))
USAGE_FILE = llm.DATA_DIR / "api_usage.json"

app = FastAPI(title="Receipted API", version="1.0",
              description="Checks a receipt image against a claim, a price list and a policy; every issue cites evidence.")


def _usage_today() -> int:
    try:
        u = json.loads(USAGE_FILE.read_text())
        return u["count"] if u.get("date") == str(dt.date.today()) else 0
    except (OSError, ValueError):
        return 0


def _count_usage() -> None:
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps({"date": str(dt.date.today()), "count": _usage_today() + 1}))


@app.get("/health")
def health():
    return {"ok": True, "model": llm.DEFAULT_MODEL, "checks_today": _usage_today(), "daily_cap": DAILY_CAP}


@app.post("/check")
async def check(image: UploadFile = File(...), claim: str = Form(...), model: str = Form(llm.DEFAULT_MODEL),
                x_api_token: str = Header(default="")):
    if not API_TOKEN or x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="missing or wrong X-Api-Token")
    if _usage_today() >= DAILY_CAP:
        raise HTTPException(status_code=429, detail=f"daily cap of {DAILY_CAP} checks reached")
    try:
        claim_obj = json.loads(claim)
    except ValueError:
        raise HTTPException(status_code=400, detail="claim must be a JSON object")
    if "amount" not in claim_obj:
        raise HTTPException(status_code=400, detail="claim needs at least an amount")
    claim_obj.setdefault("claim_id", f"API-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}")
    claim_obj.setdefault("items", [])

    suffix = Path(image.filename or "receipt.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=str(llm.DATA_DIR)) as tmp:
        tmp.write(await image.read())
        path = tmp.name
    try:
        state = run_claim(path, claim_obj, model=model, register=True, source="api")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    _count_usage()
    receipt = state.get("receipt") or {}
    return {
        "claim_id": claim_obj["claim_id"],
        "decision": state["decision"],
        "decision_reason": state["decision_reason"],
        "currency": receipt.get("currency"),
        "receipt_total": receipt.get("total"),
        "readability": receipt.get("readability"),
        "items": [{k: i.get(k) for k in ("name", "qty", "unit_price", "line_total", "confidence", "raw_line")} for i in receipt.get("items", [])],
        "verified_issues": [{k: i.get(k) for k in ("type", "severity", "message", "receipt_line", "clause_id", "price_item", "evidence")}
                            for i in state["verified_issues"]],
        "dropped_by_verifier": len(state["dropped_issues"]),
        "draft": state["draft"],
        "total_cost_usd": state["total_cost_usd"],
        "total_seconds": state["total_seconds"],
        "model": state["model"],
    }


handler = Mangum(app)   # the AWS Lambda entry point
