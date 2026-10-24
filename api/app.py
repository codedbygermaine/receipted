"""HTTP API for Receipted: POST a receipt image and a claim, get the decision, issues, evidence and draft.

Two modes:
  - synchronous (local, `uvicorn api.app:app`): POST /check returns the result directly.
  - asynchronous (AWS, RECEIPTED_ASYNC=1): POST /check stores the inputs in S3, starts the check as a
    background Lambda invocation and returns 202 with a job id; GET /jobs/{id} returns the result when
    ready. API Gateway cuts any request at 30 s and a cold start plus three model calls can take longer,
    so long work runs as a job, the way production document pipelines do.

Every /check needs the token in X-Api-Token, and a daily cap stops a public URL from running up the bill.
"""

import base64
import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from mangum import Mangum

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# On Lambda the image is read-only except /tmp. The embedding model was baked into the image at BAKED_HOME;
# copy it to a writable HOME once per container so Chroma never tries to write into the image.
BAKED_HOME = os.environ.get("RECEIPTED_BAKED_HOME")
if BAKED_HOME and os.environ.get("RECEIPTED_DATA_DIR"):
    home = Path(os.environ["RECEIPTED_DATA_DIR"]) / "home"
    if not (home / ".cache").exists():
        home.mkdir(parents=True, exist_ok=True)
        shutil.copytree(Path(BAKED_HOME) / ".cache", home / ".cache", dirs_exist_ok=True)
    os.environ["HOME"] = str(home)

from receipted import llm                     # noqa: E402
from receipted.graph import run_claim         # noqa: E402

API_TOKEN = os.environ.get("RECEIPTED_API_TOKEN", "")
DAILY_CAP = int(os.environ.get("RECEIPTED_DAILY_CAP", "100"))
ASYNC = os.environ.get("RECEIPTED_ASYNC") == "1"
BUCKET = os.environ.get("RECEIPTED_BUCKET", "")
FUNCTION_NAME = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "")
USAGE_FILE = llm.DATA_DIR / "api_usage.json"

app = FastAPI(title="Receipted API", version="1.1",
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


def _result_payload(state: dict, claim_obj: dict) -> dict:
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


def run_check(image_bytes: bytes, suffix: str, claim_obj: dict, model: str) -> dict:
    """The actual work, shared by the synchronous route and the background job."""
    llm.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=str(llm.DATA_DIR)) as tmp:
        tmp.write(image_bytes)
        path = tmp.name
    try:
        state = run_claim(path, claim_obj, model=model, register=True, source="api")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    return _result_payload(state, claim_obj)


def _parse_claim(claim: str) -> dict:
    try:
        claim_obj = json.loads(claim)
    except ValueError:
        raise HTTPException(status_code=400, detail="claim must be a JSON object")
    if not isinstance(claim_obj, dict) or "amount" not in claim_obj:
        raise HTTPException(status_code=400, detail="claim needs at least an amount")
    claim_obj.setdefault("claim_id", f"API-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}")
    claim_obj.setdefault("items", [])
    return claim_obj


@app.get("/health")
def health():
    return {"ok": True, "model": llm.DEFAULT_MODEL, "mode": "async" if ASYNC else "sync",
            "checks_today": _usage_today(), "daily_cap": DAILY_CAP}


@app.post("/check")
async def check(image: UploadFile = File(...), claim: str = Form(...), model: str = Form(llm.DEFAULT_MODEL),
                x_api_token: str = Header(default="")):
    if not API_TOKEN or x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="missing or wrong X-Api-Token")
    if _usage_today() >= DAILY_CAP:
        raise HTTPException(status_code=429, detail=f"daily cap of {DAILY_CAP} checks reached")
    claim_obj = _parse_claim(claim)
    suffix = Path(image.filename or "receipt.jpg").suffix.lower() or ".jpg"
    data = await image.read()
    _count_usage()

    if not ASYNC:
        return run_check(data, suffix, claim_obj, model)

    import boto3
    job_id = uuid.uuid4().hex
    s3 = boto3.client("s3")
    s3.put_object(Bucket=BUCKET, Key=f"jobs/{job_id}/input{suffix}", Body=data)
    s3.put_object(Bucket=BUCKET, Key=f"jobs/{job_id}/claim.json",
                  Body=json.dumps({"claim": claim_obj, "model": model, "suffix": suffix}).encode())
    boto3.client("lambda").invoke(FunctionName=FUNCTION_NAME, InvocationType="Event",
                                  Payload=json.dumps({"receipted_job": job_id}).encode())
    return JSONResponse(status_code=202, content={"job_id": job_id, "status": "queued",
                                                  "poll": f"/jobs/{job_id}", "claim_id": claim_obj["claim_id"]})


@app.get("/jobs/{job_id}")
def job_status(job_id: str, x_api_token: str = Header(default="")):
    if not API_TOKEN or x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="missing or wrong X-Api-Token")
    if not ASYNC:
        raise HTTPException(status_code=404, detail="jobs exist only in async mode")
    import boto3
    s3 = boto3.client("s3")
    for name, code in (("result.json", 200), ("error.json", 500)):
        try:
            body = s3.get_object(Bucket=BUCKET, Key=f"jobs/{job_id}/{name}")["Body"].read()
            return JSONResponse(status_code=code, content=json.loads(body))
        except s3.exceptions.NoSuchKey:
            continue
    try:
        s3.head_object(Bucket=BUCKET, Key=f"jobs/{job_id}/claim.json")
    except Exception:
        raise HTTPException(status_code=404, detail="unknown job")
    return JSONResponse(status_code=202, content={"job_id": job_id, "status": "running"})


def run_job(job_id: str) -> None:
    """Background Lambda invocation: read the inputs from S3, run the check, write the result."""
    import boto3
    s3 = boto3.client("s3")
    meta = json.loads(s3.get_object(Bucket=BUCKET, Key=f"jobs/{job_id}/claim.json")["Body"].read())
    data = s3.get_object(Bucket=BUCKET, Key=f"jobs/{job_id}/input{meta['suffix']}")["Body"].read()
    try:
        result = run_check(data, meta["suffix"], meta["claim"], meta["model"])
        s3.put_object(Bucket=BUCKET, Key=f"jobs/{job_id}/result.json", Body=json.dumps(result).encode())
    except Exception as e:
        s3.put_object(Bucket=BUCKET, Key=f"jobs/{job_id}/error.json",
                      Body=json.dumps({"job_id": job_id, "status": "failed", "error": f"{type(e).__name__}: {str(e)[:300]}"}).encode())
        raise


_mangum = Mangum(app)


def handler(event, context):
    """Lambda entry point: a background job event, or an HTTP request from API Gateway."""
    if isinstance(event, dict) and "receipted_job" in event:
        run_job(event["receipted_job"])
        return {"ok": True}
    return _mangum(event, context)
