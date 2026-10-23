"""Receipted demo. Run locally:  .venv/bin/streamlit run app/streamlit_app.py

Pick a sample receipt or upload one, enter the claim, and read the verdict: every issue with its evidence,
the draft reply, and a trace with timings and cost. The Review queue tab is what a treasurer would use.
"""

import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # so the app runs on Streamlit Cloud without `pip install -e .`

# Streamlit Community Cloud runs on Linux with a SQLite older than Chroma needs; swap in the bundled one there.
if sys.platform.startswith("linux"):
    try:
        __import__("pysqlite3")
        sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    except ImportError:
        pass

try:
    if "ANTHROPIC_API_KEY" in st.secrets:   # Streamlit Cloud keeps the key in secrets; locally .env is used
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

from receipted import audit, llm                                          # noqa: E402
from receipted.graph import pending_reviews, resume_review, run_claim     # noqa: E402

DAILY_CAP = 30
USAGE_FILE = llm.DATA_DIR / "usage.json"

# (label, image, claimed amount, purpose, items text, what to expect)
SAMPLES = [
    ("Brunch for 3", "data/external/singapore/sg_24.jpg", 101.90, "Team brunch, 3 people",
     "Eggs Benedict, 1, 28.00\nBrussels Salad, 1, 27.00\nSymmetry Breakfast, 1, 30.00", "clean claim → approve"),
    ("Pharmacy run", "data/external/singapore/sg_09.jpg", 20.40, "Supplies for event",
     "W22 Unscented Baby Wipes, 2, 3.50\nW21 Transparent Plasters, 2, 4.55\nActal Tablet, 1, 4.80\nImodium Cap, 1, 7.55", "medicines → personal items (C6)"),
    ("Café, over-claimed", "data/external/singapore/sg_23.jpg", 130.00, "Committee lunch, 4 people", "", "claim above receipt → reject"),
    ("Cinema, no purpose", "data/external/singapore/sg_03.jpg", 67.50, "", "SAFRA Movie Perks, 5, 67.50", "no purpose → needs review"),
    ("Bakery (IDR)", "app/samples/validation_000.jpg", 45500, "Snacks for orientation booth, 5 people",
     "Real Ganache, 1, 16500\nEgg Tart, 1, 13000\nPizza Toast, 1, 16000", "clean claim → approve"),
    ("Dinner + beer (IDR)", "app/samples/validation_025.jpg", 250000, "Committee dinner, 4 people",
     "Sop Sui Jiao, 1, 33000\nHa Kaou Udang, 1, 28000\nSiomay Kombinasi, 2, 46000\nBir Bintang, 2, 70000", "inflated, beer not on receipt → reject"),
]
BADGE = {"approve": ("APPROVED", "#0b7a3b", "#e3f5ea"), "needs_review": ("NEEDS A REVIEWER", "#9a6200", "#fff3d6"),
         "reject": ("REJECTED", "#b3261e", "#fde7e5")}
SEV = {"high": "#b3261e", "medium": "#c77a00", "low": "#6b7280"}

CSS = """
<style>
#MainMenu, footer, header[data-testid="stHeader"] {visibility: hidden; height: 0;}
.block-container {padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1180px;}
h1 {font-size: 2.1rem; letter-spacing: -0.02em; margin-bottom: 0.1rem;}
.rc-sub {color: #5b6168; font-size: 1.02rem; margin-bottom: 1.1rem;}
.rc-chips {display: flex; gap: 10px; flex-wrap: wrap; margin: 0 0 1.4rem 0;}
.rc-chip {background: #eef2fb; color: #1f3f7a; border-radius: 999px; padding: 6px 13px; font-size: 0.86rem; font-weight: 600;}
.rc-chip span {font-weight: 400; color: #4d5a73;}
.rc-step {font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: #6b7280; font-weight: 700; margin: 0.6rem 0 0.2rem;}
.rc-banner {border-radius: 12px; padding: 16px 20px; margin: 4px 0 14px 0; display: flex; align-items: center; gap: 16px;}
.rc-banner .rc-label {font-weight: 800; font-size: 1.25rem; letter-spacing: 0.02em;}
.rc-banner .rc-why {font-size: 0.95rem; opacity: 0.9;}
.rc-issue {border: 1px solid #e3e5e1; border-left: 6px solid #999; border-radius: 10px; padding: 12px 16px; margin: 10px 0; background: #fff;}
.rc-issue .rc-head {display: flex; justify-content: space-between; align-items: baseline;}
.rc-issue .rc-type {font-weight: 700; font-size: 1rem;}
.rc-issue .rc-sev {font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em; padding: 2px 8px; border-radius: 6px; color: #fff;}
.rc-issue .rc-msg {margin: 6px 0 4px 0; color: #222;}
.rc-issue code {background: #f3f4f1; padding: 2px 6px; border-radius: 5px; font-size: 0.85rem;}
.rc-issue .rc-clause {font-size: 0.86rem; color: #3f4650; background: #f6f7f4; border-radius: 8px; padding: 8px 10px; margin-top: 8px;}
.rc-issue .rc-ev {font-size: 0.8rem; color: #6b7280; margin-top: 6px;}
.rc-draft {background: #f6f7f4; border-left: 4px solid #1f5fbf; border-radius: 8px; padding: 14px 18px; white-space: pre-wrap; font-size: 0.97rem; line-height: 1.5;}
.rc-muted {color: #6b7280; font-size: 0.85rem;}
div[data-testid="stMetric"] {background: #fff; border: 1px solid #e3e5e1; border-radius: 10px; padding: 10px 14px;}
div[data-testid="stMetric"] label {font-size: 0.78rem;}
div[data-testid="stMetricValue"] {font-size: 1.45rem;}
</style>
"""


def usage_today() -> int:
    try:
        u = json.loads(USAGE_FILE.read_text())
        return u["count"] if u.get("date") == str(dt.date.today()) else 0
    except (OSError, ValueError):
        return 0


def record_usage() -> None:
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps({"date": str(dt.date.today()), "count": usage_today() + 1}))


def parse_items(text: str) -> list[dict]:
    items = []
    for line in text.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if not parts or not parts[0]:
            continue
        item = {"name": parts[0], "qty": 1, "line_total": None}
        for key, idx in (("qty", 1), ("line_total", 2)):
            if len(parts) > idx and parts[idx]:
                v = float(parts[idx]); item[key] = int(v) if v.is_integer() else v
        items.append(item)
    return items


def money(v, cur):
    if v is None:
        return "—"
    return f"{cur or ''} {v:,.0f}" if float(v).is_integer() and (cur or "IDR") == "IDR" else f"{cur or ''} {v:,.2f}"


def headline_numbers() -> dict:
    try:
        m = json.loads((ROOT / "results" / "metrics.json").read_text())
        c = m["checks"]; p = c["planted"]
        return {"caught": f"{sum(v['caught'] for v in p.values())}/{sum(v['n'] for v in p.values())}",
                "f1": f"{m['extraction']['claude-haiku-5-5']['item_f1']:.2f}",
                "cost": f"${c['mean_cost_usd_per_claim']:.4f}"}
    except Exception:
        return {}


def issue_card(i: dict) -> str:
    sev = i["severity"]; ev = i.get("evidence") or {}
    numbers = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in ev.items() if k not in ("clause_text",)}
    html = [f'<div class="rc-issue" style="border-left-color:{SEV[sev]}">',
            f'<div class="rc-head"><span class="rc-type">{i["type"].replace("_", " ").capitalize()}</span>'
            f'<span class="rc-sev" style="background:{SEV[sev]}">{sev}</span></div>',
            f'<div class="rc-msg">{i["message"]}</div>']
    if i.get("receipt_line"):
        html.append(f'<div>on the receipt: <code>{i["receipt_line"]}</code></div>')
    if ev.get("clause_text"):
        html.append(f'<div class="rc-clause">{ev["clause_text"]}</div>')
    if numbers:
        html.append('<div class="rc-ev">evidence: ' + ", ".join(f"{k} = {v}" for k, v in numbers.items()) + f' · found by {i["source"]}</div>')
    html.append("</div>")
    return "".join(html)


def render_result(state: dict, claim: dict) -> None:
    receipt = state.get("receipt") or {}
    cur = receipt.get("currency") or ""
    label, fg, bg = BADGE[state["decision"]]
    if state.get("paused_for_review"):
        st.info(f"Paused for a reviewer as **{claim['claim_id']}**. Decide it in the **Review queue** tab.")
    st.markdown(f'<div class="rc-banner" style="background:{bg};color:{fg}"><span class="rc-label">{label}</span>'
                f'<span class="rc-why">{state["decision_reason"]}</span></div>', unsafe_allow_html=True)
    issues = state["verified_issues"]
    def num(v):
        return "—" if v is None else (f"{v:,.0f}" if float(v).is_integer() and (cur or "IDR") == "IDR" else f"{v:,.2f}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"Claimed ({cur or '?'})", num(claim["amount"]))
    m2.metric(f"Receipt total ({cur or '?'})", num(receipt.get("total")))
    m3.metric("Issues", f"{len(issues)}", help=f"{len(state['dropped_issues'])} unsupported issue(s) dropped by the verifier")
    m4.metric("Cost of this check", f"{state['total_cost_usd']*100:.2f}¢")

    st.markdown('<div class="rc-step">What the receipt says</div>', unsafe_allow_html=True)
    if receipt:
        st.dataframe([{"qty": i["qty"], "item": i["name"], "unit price": i["unit_price"], "line total": i["line_total"],
                       "confidence": i.get("confidence", ""), "as printed": i["raw_line"]}
                      for i in receipt["items"]], width="stretch", hide_index=True, height=min(380, 42 + 35 * len(receipt["items"])))
        st.markdown(f'<div class="rc-muted">subtotal {money(receipt.get("subtotal"), cur)} · tax {money(receipt.get("tax"), cur)} · '
                    f'service {money(receipt.get("service"), cur)} · <b>total {money(receipt.get("total"), cur)}</b> '
                    f'(confidence {receipt.get("total_confidence", "?")}) · readability {receipt.get("readability")}</div>', unsafe_allow_html=True)
    else:
        st.warning(f"The receipt could not be read: {state.get('error')}")

    st.markdown('<div class="rc-step">Issues with evidence</div>', unsafe_allow_html=True)
    if not issues:
        st.success("No issue with evidence was found.")
    for i in issues:
        st.markdown(issue_card(i), unsafe_allow_html=True)
    if state["dropped_issues"]:
        with st.expander(f"{len(state['dropped_issues'])} issue(s) the model raised but could not back with evidence"):
            for d in state["dropped_issues"]:
                st.markdown(f"- **{d['type']}** ({d.get('clause_id') or d.get('price_item')}): {d['dropped_because']}")

    st.markdown('<div class="rc-step">Reply to the member</div>', unsafe_allow_html=True)
    if state.get("draft"):
        st.markdown(f'<div class="rc-draft">{state["draft"]}</div>', unsafe_allow_html=True)
    else:
        st.caption("The reply is written once a reviewer decides.")
    with st.expander("Trace: every step, its time and cost"):
        st.dataframe([{"step": e["node"], "seconds": e["seconds"], "tokens in": e.get("input_tokens"), "tokens out": e.get("output_tokens"),
                       "cost $": e.get("cost_usd"), "cached": e.get("cached"), "what happened": e["summary"]} for e in state["trace"]],
                     width="stretch", hide_index=True)


# ---------------------------------------------------------------------------------------------------
st.set_page_config(page_title="Receipted", page_icon="🧾", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("# Receipted")
st.markdown('<div class="rc-sub">Reads a receipt photo, checks it against the claim, the price list and the policy, '
            'and flags problems only when it can point at the evidence.</div>', unsafe_allow_html=True)
hn = headline_numbers()
if hn:
    st.markdown(f'<div class="rc-chips"><div class="rc-chip">{hn["caught"]} <span>planted errors caught</span></div>'
                f'<div class="rc-chip">{hn["f1"]} <span>item F1 on 100 real receipts</span></div>'
                f'<div class="rc-chip">{hn["cost"]} <span>per claim</span></div>'
                f'<div class="rc-chip">SGD · IDR <span>policy follows the receipt\'s currency</span></div></div>', unsafe_allow_html=True)

tab_check, tab_review, tab_audit, tab_how = st.tabs(["Check a claim", "Review queue", "Audit log", "How it works"])

with tab_check:
    left, right = st.columns([0.95, 1.55], gap="large")
    with left:
        st.markdown('<div class="rc-step">1 · Receipt</div>', unsafe_allow_html=True)
        labels = [s[0] for s in SAMPLES]
        choice = st.radio("Sample receipts", labels + ["Upload my own"], horizontal=True, label_visibility="collapsed")
        image_path, s_amount, s_purpose, s_items, s_expect = None, 0.0, "", "", ""
        if choice == "Upload my own":
            upload = st.file_uploader("Photo of the receipt", type=["png", "jpg", "jpeg"])
            if upload is not None:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload.name).suffix); tmp.write(upload.getvalue()); tmp.close()
                image_path = Path(tmp.name)
        else:
            _, s_path, s_amount, s_purpose, s_items, s_expect = SAMPLES[labels.index(choice)]
            image_path = ROOT / s_path
            st.caption(f"Expected: {s_expect}")
        if image_path is not None:
            st.image(str(image_path), width=300)

        st.markdown('<div class="rc-step">2 · Claim</div>', unsafe_allow_html=True)
        submitter = st.text_input("Submitted by", "A. Member")
        purpose = st.text_input("Purpose (and how many people, for meals)", s_purpose, placeholder="e.g. Team lunch, 4 people")
        amount = st.number_input("Amount claimed, in the receipt's currency", min_value=0.0, value=float(s_amount), step=0.5, format="%.2f")
        items_text = st.text_area("Items claimed: name, qty, line total (one per line)", s_items, height=110)
        with st.expander("Options"):
            model = st.selectbox("Model", [llm.DEFAULT_MODEL, llm.LARGE_MODEL])
            pause = st.checkbox("Pause for a reviewer when the decision is needs_review", value=True)
        run = st.button("Check this claim", type="primary", disabled=image_path is None, width="stretch")

    with right:
        if run:
            if usage_today() >= DAILY_CAP:
                st.error(f"Daily limit of {DAILY_CAP} checks reached on this demo. Try again tomorrow.")
                st.stop()
            claim = {"claim_id": f"DEMO-{dt.datetime.now().strftime('%H%M%S')}", "submitter": submitter, "purpose": purpose,
                     "amount": int(amount) if float(amount).is_integer() else float(amount), "currency": "", "items": parse_items(items_text)}
            with st.status("Reading the receipt and running the checks…", expanded=False) as status:
                state = run_claim(image_path, claim, model=model, register=True, review=pause, source="app")
                status.update(label=f"Done in {state['total_seconds']:.0f}s", state="complete")
            if not all(e.get("cached") for e in state["trace"] if "cost_usd" in e):
                record_usage()
            render_result(state, claim)
        else:
            st.markdown('<div class="rc-step">Verdict</div>', unsafe_allow_html=True)
            st.markdown("Pick a sample on the left, or upload a receipt, fill in the claim and press **Check this claim**. "
                        "You'll get the decision, every issue with the receipt line and policy clause it rests on, and the reply to send.")
            st.markdown("**What makes it trustworthy**")
            st.markdown("- The arithmetic is done in plain code, not by the model.\n"
                        "- Every flagged issue must cite a receipt line and a policy clause; a verifier throws away anything that doesn't.\n"
                        "- Unreadable receipts and borderline cases go to a person instead of being guessed.\n"
                        "- Measured on 100 real receipts with planted errors, two models, a hallucination probe and a human check of the judge.")

with tab_review:
    st.markdown('<div class="rc-step">Claims waiting for a person</div>', unsafe_allow_html=True)
    st.caption("The reviewer sees the receipt, the extracted lines with their confidence, each issue with its evidence, and decides. "
               "The decision resumes the paused run and the member's reply is written from it.")
    try:
        pending = pending_reviews()
    except Exception as e:
        st.error(f"Review queue unavailable: {type(e).__name__}: {e}"); pending = []
    if not pending:
        st.info("Nothing waiting. Run a claim with the pause option on and a needs-review outcome to see one here.")
    for pz in pending:
        with st.container(border=True):
            st.markdown(f"**{pz['claim_id']}** · {pz['submitter']} · claimed {pz['amount']} · purpose: {pz['purpose'] or '(none)'}")
            st.caption(f"Why it is here: {pz['reason']}")
            c1, c2 = st.columns([1, 1.7])
            with c1:
                if pz.get("image_path") and Path(pz["image_path"]).exists():
                    st.image(pz["image_path"], width="stretch")
            with c2:
                rc = pz.get("receipt") or {}
                if rc.get("items"):
                    st.dataframe([{"qty": i["qty"], "item": i["name"], "line total": i["line_total"], "confidence": i.get("confidence", "")}
                                  for i in rc["items"]], width="stretch", hide_index=True, height=min(300, 42 + 35 * len(rc["items"])))
                for i in pz["issues_full"]:
                    st.markdown(issue_card(i), unsafe_allow_html=True)
            with st.form(key=f"review-{pz['claim_id']}"):
                note = st.text_input("Reviewer note (goes into the reply to the member)")
                a, b = st.columns(2)
                approve = a.form_submit_button("Approve", type="primary", width="stretch")
                reject = b.form_submit_button("Reject", width="stretch")
                if approve or reject:
                    done = resume_review(pz["claim_id"], "approve" if approve else "reject", note)
                    st.success(f"{pz['claim_id']} → {done['decision'].upper()}")
                    st.markdown(f'<div class="rc-draft">{done["draft"]}</div>', unsafe_allow_html=True)

with tab_audit:
    st.markdown('<div class="rc-step">Every decision, with its evidence</div>', unsafe_allow_html=True)
    try:
        entries = audit.recent(30); samples = audit.audit_samples()
    except Exception as e:
        st.error(f"Audit log unavailable: {type(e).__name__}: {e}"); entries, samples = [], []
    if samples:
        st.warning(f"{len(samples)} approved claim(s) picked for a random spot-check (1 in {audit.AUDIT_SAMPLE_RATE}): "
                   + ", ".join(e["claim_id"] for e in samples[:10]))
    if not entries:
        st.info("No decisions logged yet.")
    else:
        st.dataframe([{"time": e["at"][:19].replace("T", " "), "source": e["source"], "claim": e["claim_id"], "amount": e["claimed_amount"],
                       "currency": e["currency"], "decision": e["decision"], "by a person": e["reviewed_by_human"],
                       "spot-check": e.get("audit_sample", False), "issues": len(e["issues"]), "dropped": e["dropped_by_verifier"],
                       "cost $": e["cost_usd"]} for e in entries], width="stretch", hide_index=True)
        st.caption("Each row is one line in data/audit_log.jsonl with the full issues, evidence, prompt versions and cost. "
                   "Reviewer decisions are also written to data/review_corrections.json as labelled cases for the next evaluation.")

with tab_how:
    st.graphviz_chart("""
    digraph G {
      rankdir=LR; bgcolor="transparent"; node [shape=box, style="rounded,filled", fillcolor="#eef2fb", color="#c9d4ee", fontname="Helvetica", fontsize=11];
      extract [label="extract\\nmultimodal LLM → JSON schema"];
      maths [label="maths_check\\nPython arithmetic + claim matching"];
      retrieve [label="retrieve\\nChroma: policy clauses + price rows"];
      rules [label="rule_check\\nLLM, must cite clause + receipt line"];
      verify [label="verify\\nPython drops issues without evidence"];
      decide [label="decide\\napprove / needs_review / reject"];
      review [label="human_review\\npause, checkpoint, resume", fillcolor="#fff3d6", color="#e8c98a"];
      draft [label="draft\\nreply to the member"];
      extract -> maths -> retrieve -> rules -> verify -> decide -> draft;
      decide -> review -> draft [style=dashed];
      extract -> decide [label="unreadable", style=dashed];
    }""")
    st.markdown("""
**Each job goes to the right tool.** The image model reads the messy photo. Plain Python does the arithmetic, because language
models are unreliable at maths and code is exact. A vector store finds the policy clauses and price-list rows that matter.
The rule-check model may raise an issue only if it cites a clause *and* a receipt line, and for large claims it is asked three times and only the majority counts.

**Every flag needs evidence.** The verifier, in plain Python, throws away any issue whose clause does not exist in the policy,
whose receipt line is not in the extraction, or whose price comparison does not hold when re-done in code.

**It knows when to pass to a human.** Unreadable receipts, low-confidence lines and borderline findings pause for a reviewer,
who decides from the queue; the reply is written from the human's decision. Every decision is audit-logged, and one approved claim in ten is spot-checked.

**It is measured.** Extraction against CORD ground truth, the checks on 100 test claims with planted errors, drafts by a larger model
as judge and by a person, a hallucination probe, and receipts from four other countries. All numbers in the README come from `results/`.

*Data: CORD v2 (CC BY 4.0) and receipts photographed by me. The claims, price lists and policies were written by me for testing.*
""")
