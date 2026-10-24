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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# On Lambda the image is read-only except /tmp, and the embedding model was baked into the image at BAKED_HOME.
# HOME points at a writable folder in /tmp, with a symlink to the baked model so Chroma finds it without downloading.
# (Copying the 80 MB model instead ran past Lambda's 10 s init window; a symlink is instant.)
BAKED_HOME = os.environ.get("RECEIPTED_BAKED_HOME")
if BAKED_HOME and os.environ.get("RECEIPTED_DATA_DIR"):
    home = Path(os.environ["RECEIPTED_DATA_DIR"]) / "home"
    link = home / ".cache" / "chroma" / "onnx_models"
    if not link.exists():
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(Path(BAKED_HOME) / ".cache" / "chroma" / "onnx_models")
    os.environ["HOME"] = str(home)
    # The policy index was built into the image too (a persistent Chroma store, ~1.5 MB). Chroma needs to write
    # to its store, so copy it to /tmp once per container; the alternative, re-embedding every clause and price
    # row on each invocation, cost ~40 s on Lambda's CPU.
    baked_db = Path(BAKED_HOME).parent / "chroma_db"
    runtime_db = Path(os.environ["RECEIPTED_DATA_DIR"]) / "chroma_db"
    if baked_db.exists() and not runtime_db.exists():
        shutil.copytree(baked_db, runtime_db)
    os.environ.setdefault("RECEIPTED_CHROMA_PATH", str(runtime_db))

from receipted import llm                     # noqa: E402
from receipted.graph import run_claim         # noqa: E402

API_TOKEN = os.environ.get("RECEIPTED_API_TOKEN", "")
DEMO_TOKEN = os.environ.get("RECEIPTED_DEMO_TOKEN", "")          # embedded in the public web demo; small cap
DAILY_CAP = int(os.environ.get("RECEIPTED_DAILY_CAP", "100"))
DEMO_DAILY_CAP = int(os.environ.get("RECEIPTED_DEMO_DAILY_CAP", "40"))
ASYNC = os.environ.get("RECEIPTED_ASYNC") == "1"
BUCKET = os.environ.get("RECEIPTED_BUCKET", "")
FUNCTION_NAME = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "")
USAGE_FILE = llm.DATA_DIR / "api_usage.json"   # per container; the S3-backed count below is what the demo cap uses

app = FastAPI(title="Receipted API", version="1.2",
              description="Checks a receipt image against a claim, a price list and a policy; every issue cites evidence.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])


def _auth(token: str) -> str:
    """Returns 'full' or 'demo', or raises. Usage caps are tracked per tier."""
    if API_TOKEN and token == API_TOKEN:
        return "full"
    if DEMO_TOKEN and token == DEMO_TOKEN:
        return "demo"
    raise HTTPException(status_code=401, detail="missing or wrong X-Api-Token")


def _usage_key(tier: str) -> str:
    return f"usage/{tier}/{dt.date.today()}.json"


def _usage_today(tier: str = "full") -> int:
    if ASYNC:
        import boto3
        s3 = boto3.client("s3")
        try:
            return json.loads(s3.get_object(Bucket=BUCKET, Key=_usage_key(tier))["Body"].read())["count"]
        except Exception:
            return 0
    try:
        u = json.loads(USAGE_FILE.read_text())
        return u["count"] if u.get("date") == str(dt.date.today()) and u.get("tier") == tier else 0
    except (OSError, ValueError):
        return 0


def _count_usage(tier: str = "full") -> None:
    n = _usage_today(tier) + 1
    if ASYNC:
        import boto3
        boto3.client("s3").put_object(Bucket=BUCKET, Key=_usage_key(tier), Body=json.dumps({"count": n}).encode())
        return
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps({"date": str(dt.date.today()), "tier": tier, "count": n}))


def _result_payload(state: dict, claim_obj: dict) -> dict:
    receipt = state.get("receipt") or {}
    return {
        "claim_id": claim_obj["claim_id"],
        "submitter": claim_obj.get("submitter", "member"),
        "purpose": claim_obj.get("purpose", ""),
        "claimed_amount": claim_obj.get("amount"),
        "image_key": None,
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
        "trace": [{k: e.get(k) for k in ("node", "seconds", "cached")} for e in state.get("trace", [])],   # where the time went
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
def health(warm: int = 0):
    # The web page calls /health?warm=1 while the visitor fills in the form, so the embedding model (about 20 s
    # to load on a cold Lambda) is already in memory by the time the claim arrives.
    if warm:
        from receipted.retrieve import retrieve_policy
        retrieve_policy("warm-up", k=1, currency="SGD"); retrieve_policy("warm-up", k=1, currency="IDR")
    return {"ok": True, "model": llm.DEFAULT_MODEL, "mode": "async" if ASYNC else "sync",
            "demo_checks_today": _usage_today("demo"), "demo_daily_cap": DEMO_DAILY_CAP}


@app.post("/check")
async def check(image: UploadFile = File(...), claim: str = Form(...), model: str = Form(llm.DEFAULT_MODEL),
                x_api_token: str = Header(default="")):
    tier = _auth(x_api_token)
    cap = DEMO_DAILY_CAP if tier == "demo" else DAILY_CAP
    if _usage_today(tier) >= cap:
        raise HTTPException(status_code=429, detail=f"the public demo's budget of {cap} checks a day is used up; try again tomorrow")
    claim_obj = _parse_claim(claim)
    suffix = Path(image.filename or "receipt.jpg").suffix.lower() or ".jpg"
    data = await image.read()
    if len(data) > 8_000_000:
        raise HTTPException(status_code=413, detail="image larger than 8 MB")
    _count_usage(tier)

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
    _auth(x_api_token)
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


@app.get("/jobs/{job_id}/image")
def job_image(job_id: str, x_api_token: str = Header(default="")):
    """The receipt image for a job, base64, so the approvals inbox can show it."""
    _auth(x_api_token)
    if not ASYNC:
        raise HTTPException(status_code=404, detail="images are stored only in async mode")
    import boto3
    s3 = boto3.client("s3")
    meta = json.loads(s3.get_object(Bucket=BUCKET, Key=f"jobs/{job_id}/claim.json")["Body"].read())
    data = s3.get_object(Bucket=BUCKET, Key=f"jobs/{job_id}/input{meta['suffix']}")["Body"].read()
    mime = "image/png" if meta["suffix"] == ".png" else "image/jpeg"
    return {"data_url": f"data:{mime};base64," + base64.b64encode(data).decode()}


class Decision(BaseModel):
    decision: str   # approve | reject
    note: str = ""
    reviewer: str = "Finance"


@app.get("/inbox")
def inbox(x_api_token: str = Header(default="")):
    """Claims waiting for an approver: job results whose decision is needs_review and that nobody has decided."""
    _auth(x_api_token)
    if not ASYNC:
        return {"pending": [], "decided": []}
    import boto3
    s3 = boto3.client("s3")
    pending, decided = [], []
    token = None
    while True:
        kw = {"Bucket": BUCKET, "Prefix": "jobs/", "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        page = s3.list_objects_v2(**kw)
        for obj in page.get("Contents", []):
            if obj["Key"].endswith("/result.json"):
                r = json.loads(s3.get_object(Bucket=BUCKET, Key=obj["Key"])["Body"].read())
                r["job_id"] = obj["Key"].split("/")[1]
                r["submitted_at"] = obj["LastModified"].isoformat(timespec="seconds")
                (decided if r.get("human") else pending if r["decision"] == "needs_review" else decided).append(r)
        if not page.get("IsTruncated"):
            break
        token = page.get("NextContinuationToken")
    pending.sort(key=lambda r: r["submitted_at"], reverse=True)
    decided.sort(key=lambda r: r["submitted_at"], reverse=True)
    return {"pending": pending[:50], "decided": decided[:100]}


@app.post("/jobs/{job_id}/decide")
def decide_job(job_id: str, body: Decision, x_api_token: str = Header(default="")):
    """An approver decides a held claim. The reply to the claimant is rewritten from the human decision."""
    _auth(x_api_token)
    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be approve or reject")
    if not ASYNC:
        raise HTTPException(status_code=404, detail="reviews exist only in async mode")
    import boto3
    from receipted.draft import write_draft
    s3 = boto3.client("s3")
    try:
        r = json.loads(s3.get_object(Bucket=BUCKET, Key=f"jobs/{job_id}/result.json")["Body"].read())
    except s3.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="unknown job")
    if r.get("human"):
        raise HTTPException(status_code=409, detail="already decided")
    claim = {"claim_id": r["claim_id"], "submitter": r.get("submitter", "member"), "amount": r.get("claimed_amount"),
             "currency": r.get("currency")}
    receipt = {"total": r.get("receipt_total"), "currency": r.get("currency")}
    reason = f"reviewed by {body.reviewer}: {body.note}" if body.note else f"reviewed by {body.reviewer}"
    issues = [{**i, "source": "rules" if i.get("clause_id") else "maths"} for i in r["verified_issues"]]
    draft, _ = write_draft(claim, receipt, body.decision, reason, issues)
    r.update({"decision": body.decision, "decision_reason": reason, "draft": draft,
              "human": {"decision": body.decision, "note": body.note, "reviewer": body.reviewer,
                        "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}})
    s3.put_object(Bucket=BUCKET, Key=f"jobs/{job_id}/result.json", Body=json.dumps(r).encode())
    return r


def run_job(job_id: str) -> None:
    """Background Lambda invocation: read the inputs from S3, run the check, write the result."""
    import boto3
    s3 = boto3.client("s3")
    meta = json.loads(s3.get_object(Bucket=BUCKET, Key=f"jobs/{job_id}/claim.json")["Body"].read())
    data = s3.get_object(Bucket=BUCKET, Key=f"jobs/{job_id}/input{meta['suffix']}")["Body"].read()
    try:
        result = run_check(data, meta["suffix"], meta["claim"], meta["model"])
        result["image_key"] = f"jobs/{job_id}/input{meta['suffix']}"
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
