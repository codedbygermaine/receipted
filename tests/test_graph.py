from receipted.graph import decide, route_after_extract


def receipt(readability="clear", items=None, total_confidence="high"):
    return {"items": items or [], "readability": readability, "total": 1, "total_confidence": total_confidence}


def issue(sev):
    return {"severity": sev}


def test_reject_on_any_high():
    assert decide(receipt(), None, [issue("low"), issue("high")])[0] == "reject"


def test_review_on_medium():
    assert decide(receipt(), None, [issue("medium")])[0] == "needs_review"


def test_approve_when_clean_and_clear():
    assert decide(receipt(), None, [])[0] == "approve"
    assert decide(receipt(), None, [issue("low")])[0] == "approve"


def test_partly_unclear_but_legible_lines_is_approved():
    ok = [{"raw_line": "1 TEA 5,000", "confidence": "high"}]
    assert decide(receipt("partly unclear", ok), None, [])[0] == "approve"


def test_low_confidence_item_or_total_goes_to_review():
    low_item = [{"raw_line": "1 TEA 5,0?0", "confidence": "low"}]
    assert decide(receipt("partly unclear", low_item), None, [])[0] == "needs_review"
    assert decide(receipt("clear", total_confidence="low"), None, [])[0] == "needs_review"


def test_old_extractions_without_confidence_fields_still_work():
    legacy = {"items": [{"raw_line": "1 TEA 5,000"}], "readability": "clear", "total": 1}
    assert decide(legacy, None, [])[0] == "approve"


def test_unreadable_or_failed_extraction_never_approves():
    assert decide(receipt("unreadable"), None, [])[0] == "needs_review"
    assert decide(None, "invalid output twice", [])[0] == "needs_review"


def test_routing_skips_checks_when_unreadable_or_failed():
    assert route_after_extract({"error": None, "receipt": receipt("clear")}) == "maths_check"
    assert route_after_extract({"error": None, "receipt": receipt("unreadable")}) == "decide"
    assert route_after_extract({"error": "boom", "receipt": None}) == "decide"
