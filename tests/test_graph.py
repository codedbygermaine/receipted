from receipted.graph import decide, route_after_extract


def receipt(readability="clear"):
    return {"items": [], "readability": readability, "total": 1}


def issue(sev):
    return {"severity": sev}


def test_reject_on_any_high():
    assert decide(receipt(), None, [issue("low"), issue("high")])[0] == "reject"


def test_review_on_medium():
    assert decide(receipt(), None, [issue("medium")])[0] == "needs_review"


def test_approve_when_clean_and_clear():
    assert decide(receipt(), None, [])[0] == "approve"
    assert decide(receipt(), None, [issue("low")])[0] == "approve"


def test_partly_unclear_goes_to_review_even_with_no_issues():
    assert decide(receipt("partly unclear"), None, [])[0] == "needs_review"


def test_unreadable_or_failed_extraction_never_approves():
    assert decide(receipt("unreadable"), None, [])[0] == "needs_review"
    assert decide(None, "invalid output twice", [])[0] == "needs_review"


def test_routing_skips_checks_when_unreadable_or_failed():
    assert route_after_extract({"error": None, "receipt": receipt("clear")}) == "maths_check"
    assert route_after_extract({"error": None, "receipt": receipt("unreadable")}) == "decide"
    assert route_after_extract({"error": "boom", "receipt": None}) == "decide"
