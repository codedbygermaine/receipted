"""Receipted demo. Run locally:  .venv/bin/streamlit run app/streamlit_app.py

Upload a receipt (or pick a sample), enter the claim, and see the extracted table, every issue with
its evidence, the decision, the draft message and a trace with timings and cost.
"""

import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

# Streamlit Community Cloud runs on Linux with a SQLite older than Chroma needs; swap in the
# bundled pysqlite3 there. On a Mac the system SQLite is fine and the package is not installed.
if sys.platform.startswith("linux"):
    try:
        __import__("pysqlite3")
        sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    except ImportError:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # so the app runs on Streamlit Cloud without `pip install -e .`

# On Streamlit Cloud the key lives in st.secrets; locally it comes from .env (loaded by receipted.llm).
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:  # no secrets file locally: receipted.llm falls back to .env
    pass

from receipted import audit, llm                           # noqa: E402
from receipted.graph import pending_reviews, resume_review, run_claim   # noqa: E402

DAILY_CAP = 30                                  # uncached checks per day, so strangers can't run up the bill
USAGE_FILE = ROOT / "data" / "usage.json"
SAMPLES = {
    "SG brunch for 3, claim matches (SGD)": ("data/external/singapore/sg_24.jpg", 101.90, "Team brunch, 3 people",
                                              "Eggs Benedict, 1, 28.00\nBrussels Salad, 1, 27.00\nSymmetry Breakfast, 1, 30.00"),
    "SG pharmacy with medicines, personal items (SGD)": ("data/external/singapore/sg_09.jpg", 20.40, "Supplies for event",
                                                         "W22 Unscented Baby Wipes, 2, 3.50\nW21 Transparent Plasters, 2, 4.55\nActal Tablet, 1, 4.80\nImodium Cap, 1, 7.55"),
    "SG cafe, over-claimed (SGD)": ("data/external/singapore/sg_23.jpg", 130.00, "Committee lunch, 4 people", ""),
    "SG cinema tickets, no purpose (SGD)": ("data/external/singapore/sg_03.jpg", 67.50, "", "SAFRA Movie Perks, 5, 67.50"),
    "Bakery, 3 items, clean claim (IDR)": ("app/samples/validation_000.jpg", 45500,
                                     "Snacks for orientation booth, 5 people",
                                     "Real Ganache, 1, 16500\nEgg Tart, 1, 13000\nPizza Toast, 1, 16000"),
    "Restaurant, inflated claim + beer not on receipt (IDR)": ("app/samples/validation_025.jpg", 250000,
                                                        "Committee dinner, 4 people",
                                                        "Sop Sui Jiao, 1, 33000\nHa Kaou Udang, 1, 28000\nSiomay Kombinasi, 2, 46000\nBir Bintang, 2, 70000"),
    "Cafe, hot tea above price list (IDR)": ("app/samples/validation_045.jpg", 287760,
                                       "Refreshments for committee meeting, 6 people", ""),
    "Cinema ticket, no purpose stated (IDR)": ("app/samples/validation_090.jpg", 70000, "", "Regular, 2, 70000"),
    "Fast food, claim matches (IDR)": ("app/samples/validation_004.jpg", 41000, "Lunch for volunteers, 1 person",
                                 "BBQ Chicken, 1, 41000"),
}
BADGE = {"approve": ("APPROVE", "#0ca30c"), "needs_review": ("NEEDS REVIEW", "#fab219"), "reject": ("REJECT", "#d03b3b")}


def usage_today():
    try:
        u = json.loads(USAGE_FILE.read_text())
        if u.get("date") == str(dt.date.today()):
            return u["count"]
    except (OSError, ValueError):
        pass
    return 0


def record_usage():
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps({"date": str(dt.date.today()), "count": usage_today() + 1}))


def parse_items(text):
    items = []
    for line in text.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if not parts or not parts[0]:
            continue
        item = {"name": parts[0], "qty": 1, "line_total": None}
        if len(parts) > 1 and parts[1]:
            item["qty"] = int(float(parts[1])) if float(parts[1]).is_integer() else float(parts[1])
        if len(parts) > 2 and parts[2]:
            item["line_total"] = int(float(parts[2])) if float(parts[2]).is_integer() else float(parts[2])
        items.append(item)
    return items


st.set_page_config(page_title="Receipted", page_icon="🧾", layout="wide")
st.title("Receipted")
st.caption("Reads a receipt image, checks it against a claim, a price list and a policy, and flags problems only with evidence.")

tab_check, tab_review, tab_audit, tab_how = st.tabs(["Check a claim", "Review queue", "Audit log", "How it works"])

with tab_check:
    left, right = st.columns([1, 1.4])
    with left:
        st.subheader("1. Receipt")
        sample = st.selectbox("Pick a sample receipt", ["(upload my own)"] + list(SAMPLES))
        upload = st.file_uploader("…or upload a photo", type=["png", "jpg", "jpeg"])
        if sample != "(upload my own)":
            s_path, s_amount, s_purpose, s_items = SAMPLES[sample]
            image_path = ROOT / s_path
        else:
            s_amount, s_purpose, s_items = 0, "", ""
            image_path = None
            if upload is not None:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload.name).suffix)
                tmp.write(upload.getvalue()); tmp.close()
                image_path = Path(tmp.name)
        if image_path is not None:
            st.image(str(image_path), width=320)

        st.subheader("2. Claim")
        submitter = st.text_input("Submitter", "A. Member")
        purpose = st.text_input("Purpose (e.g. 'Team lunch, 4 people')", s_purpose)
        amount = st.number_input("Amount claimed (in the receipt's currency)", min_value=0.0, value=float(s_amount), step=0.5, format="%.2f")
        items_text = st.text_area("Items claimed, one per line: name, qty, line total", s_items, height=120)
        model = st.selectbox("Model", [llm.DEFAULT_MODEL, llm.LARGE_MODEL])
        pause = st.checkbox("Pause for a reviewer when the decision is needs_review", value=True)
        run = st.button("Check this claim", type="primary", disabled=image_path is None)

    with right:
        if run:
            if usage_today() >= DAILY_CAP:
                st.error(f"Daily limit of {DAILY_CAP} checks reached. Try again tomorrow.")
                st.stop()
            claim = {"claim_id": f"DEMO-{dt.datetime.now().strftime('%H%M%S')}", "submitter": submitter, "purpose": purpose,
                     "amount": int(amount) if float(amount).is_integer() else float(amount),
                     "currency": "", "items": parse_items(items_text)}   # currency comes from the receipt
            with st.spinner("Reading the receipt and running the checks…"):
                state = run_claim(image_path, claim, model=model, register=True, review=pause, source="app")
            if not all(e.get("cached") for e in state["trace"] if "cost_usd" in e):
                record_usage()

            if state.get("paused_for_review"):
                st.warning(f"Paused for a reviewer as {claim['claim_id']}. Open the **Review queue** tab to decide it.")
            label, colour = BADGE[state["decision"]]
            st.markdown(f"<span style='background:{colour};color:white;padding:6px 14px;border-radius:6px;"
                        f"font-weight:700;font-size:1.1em'>{label}</span> &nbsp; {state['decision_reason']}",
                        unsafe_allow_html=True)

            receipt = state.get("receipt")
            st.subheader("Extracted from the receipt")
            if receipt:
                st.dataframe([{"qty": i["qty"], "item": i["name"], "unit price": i["unit_price"],
                               "line total": i["line_total"], "confidence": i.get("confidence", ""),
                               "as printed": i["raw_line"]} for i in receipt["items"]],
                             use_container_width=True, hide_index=True)
                st.caption(f"subtotal {receipt['subtotal']} · tax {receipt['tax']} · service {receipt['service']} · "
                           f"discount {receipt['discount']} · **total {receipt['total']}** "
                           f"(confidence {receipt.get('total_confidence', '?')}) · readability: {receipt['readability']}")
            else:
                st.warning(f"Extraction failed: {state.get('error')}")

            issues = state["verified_issues"]
            st.subheader(f"Issues ({len(issues)} verified, {len(state['dropped_issues'])} dropped by the verifier)")
            if not issues:
                st.success("No issues with evidence were found.")
            for i in issues:
                sev_colour = {"high": "#d03b3b", "medium": "#fab219", "low": "#52514e"}[i["severity"]]
                with st.container(border=True):
                    st.markdown(f"<span style='color:{sev_colour};font-weight:700'>{i['severity'].upper()}</span> "
                                f"**{i['type'].replace('_', ' ')}** · found by {i['source']}", unsafe_allow_html=True)
                    st.write(i["message"])
                    if i.get("receipt_line"):
                        st.code(i["receipt_line"], language=None)
                    ev = i.get("evidence") or {}
                    if ev.get("clause_text"):
                        st.info(ev["clause_text"])
                    numbers = {k: v for k, v in ev.items() if k != "clause_text"}
                    if numbers:
                        st.caption("evidence: " + ", ".join(f"{k}={v}" for k, v in numbers.items()))
            for d in state["dropped_issues"]:
                st.caption(f"Dropped by verifier: {d['type']} ({d['clause_id'] or d['price_item']}) — {d['dropped_because']}")

            st.subheader("Draft message to the submitter")
            st.text_area("draft", state["draft"], height=220, label_visibility="collapsed")

            with st.expander(f"Trace: {state['total_seconds']}s, ${state['total_cost_usd']:.4f} ({state['model']})"):
                st.dataframe([{"node": e["node"], "seconds": e["seconds"], "tokens in": e.get("input_tokens"),
                               "tokens out": e.get("output_tokens"), "cost $": e.get("cost_usd"),
                               "cached": e.get("cached"), "summary": e["summary"]} for e in state["trace"]],
                             use_container_width=True, hide_index=True)
        else:
            st.info("Pick a sample or upload a receipt, fill in the claim, and press **Check this claim**.")

with tab_review:
    st.subheader("Claims waiting for a person")
    st.caption("What a reviewer sees: the receipt, the extracted lines with their confidence, each issue with its evidence, "
               "and two buttons. The decision resumes the paused run and the draft is written from it.")
    pending = pending_reviews()
    if not pending:
        st.info("Nothing waiting. Run a claim with the pause box ticked and a needs_review outcome to see one here.")
    for pz in pending:
        with st.container(border=True):
            st.markdown(f"**{pz['claim_id']}** · {pz['submitter']} · claimed {pz['amount']} · purpose: {pz['purpose'] or '(none)'}")
            st.caption(f"Why it is here: {pz['reason']}")
            c1, c2 = st.columns([1, 1.6])
            with c1:
                if pz.get("image_path") and Path(pz["image_path"]).exists():
                    st.image(pz["image_path"], width=300)
            with c2:
                rc = pz.get("receipt") or {}
                if rc.get("items"):
                    st.dataframe([{"qty": i["qty"], "item": i["name"], "line total": i["line_total"],
                                   "confidence": i.get("confidence", "")} for i in rc["items"]],
                                 use_container_width=True, hide_index=True, height=min(300, 40 + 35 * len(rc["items"])))
                    st.caption(f"total {rc.get('total')} (confidence {rc.get('total_confidence', '?')})")
                for i in pz["issues_full"]:
                    ev = {k: v for k, v in (i.get("evidence") or {}).items() if k != "clause_text"}
                    st.markdown(f"- **{i['severity'].upper()}** {i['type'].replace('_', ' ')}: {i['message']}"
                                + (f"  \n  `{i['receipt_line']}`" if i.get("receipt_line") else "")
                                + (f"  \n  evidence: {ev}" if ev else ""))
            with st.form(key=f"review-{pz['claim_id']}"):
                note = st.text_input("Reviewer note (goes into the message to the member)")
                a, b = st.columns(2)
                approve = a.form_submit_button("Approve", type="primary")
                reject = b.form_submit_button("Reject")
                if approve or reject:
                    done = resume_review(pz["claim_id"], "approve" if approve else "reject", note)
                    st.success(f"{pz['claim_id']} → {done['decision'].upper()}")
                    st.text_area("Draft sent to the member", done["draft"], height=180)

with tab_audit:
    st.subheader("Every decision, with its evidence")
    entries = audit.recent(30)
    if not entries:
        st.info("No decisions logged yet.")
    else:
        st.dataframe([{"time": e["at"], "source": e["source"], "claim": e["claim_id"], "amount": e["claimed_amount"],
                       "currency": e["currency"], "decision": e["decision"], "human": e["reviewed_by_human"],
                       "issues": len(e["issues"]), "dropped": e["dropped_by_verifier"],
                       "model": (e.get("versions") or {}).get("model"), "cost $": e["cost_usd"]} for e in entries],
                     use_container_width=True, hide_index=True)
        st.caption("Each row is one line in data/audit_log.jsonl with the full issues, evidence, prompt versions and cost. "
                   "Reviewer decisions are also written to data/review_corrections.json as labelled cases for later evaluation.")

with tab_how:
    st.graphviz_chart("""
    digraph G {
      rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#eef3fb", fontname="Helvetica", fontsize=11];
      extract [label="extract\\nmultimodal LLM → JSON schema"];
      maths [label="maths_check\\nPython arithmetic + claim matching"];
      retrieve [label="retrieve\\nChroma: policy clauses + price rows"];
      rules [label="rule_check\\nLLM, must cite clause + receipt line"];
      verify [label="verify\\nPython drops issues without real evidence"];
      decide [label="decide\\napprove / needs_review / reject"];
      draft [label="draft\\nmessage to submitter"];
      extract -> maths -> retrieve -> rules -> verify -> decide -> draft;
      extract -> decide [label="unreadable or\\nfailed validation", style=dashed];
    }""")
    st.markdown("""
**Each job goes to the right tool.** The image model reads the messy photo. Plain Python does the arithmetic,
because language models are unreliable at maths and code is exact. A vector store finds the policy clauses and
price-list rows that matter. The rule-check model may raise an issue only if it cites a clause *and* a receipt line.

**Every flag needs evidence.** The verifier, in plain Python, throws away any issue whose clause id does not exist
in the policy, whose receipt line is not in the extraction, or whose price comparison does not hold when re-done in code.

**It knows when to pass to a human.** If the receipt is unreadable, or the extraction fails validation twice, the
checks are skipped and the claim goes straight to *needs review* instead of being guessed at.

**It is measured.** Extraction is scored against CORD ground truth; the checks are scored on 100 test claims I wrote
with planted errors; the drafts are scored by a larger model against a written rubric. See the README for numbers.

*Data: CORD v2 (CC BY 4.0). The claims, price list and policy were written by me for testing.*
""")
