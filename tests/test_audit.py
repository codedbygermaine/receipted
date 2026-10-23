import json

from receipted import audit


def test_audit_record_and_correction(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(audit, "CORRECTIONS_PATH", tmp_path / "corr.json")
    state = {"claim": {"claim_id": "X1", "submitter": "A", "amount": 10, "currency": "SGD"},
             "receipt": {"currency": "SGD", "total": 10}, "fingerprint": "abc", "decision": "needs_review",
             "decision_reason": "r", "verified_issues": [{"source": "maths", "type": "t", "severity": "medium"}],
             "dropped_issues": [], "model": "m", "total_cost_usd": 0.001, "total_seconds": 1.0}
    audit.record(state, source="cli")
    state2 = {**state, "decision": "approve", "reviewed_by_human": True}
    audit.record(state2, source="review", reviewer_note="ok")
    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["decision"] == "needs_review"
    corr = json.loads((tmp_path / "corr.json").read_text())
    assert corr == [{**corr[0]}] and corr[0]["human_decision"] == "approve" and corr[0]["reviewer_note"] == "ok"
    assert audit.recent(1)[0]["source"] == "review"
