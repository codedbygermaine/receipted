from receipted.rules import majority


def issue(clause, line, type_="x"):
    return {"source": "rules", "type": type_, "severity": "high", "message": "m", "receipt_line": line,
            "clause_id": clause, "price_item": None, "evidence": {}}


def test_majority_keeps_issues_two_of_three_runs_agree_on():
    runs = [[issue("C6", "1 ACTAL 4.80"), issue("C6", "1 IMODIUM 7.55"), issue("C6", "1 WIPES 3.50")],
            [],
            [issue("C6", "1 actal  4.80"), issue("C6", "1 IMODIUM 7.55")]]
    kept, tally = majority(runs)
    lines = sorted(i["receipt_line"] for i in kept)
    assert lines == ["1 ACTAL 4.80", "1 IMODIUM 7.55"]          # wipes appeared once: dropped
    assert all(i["evidence"]["votes"] == "2/3" for i in kept)
    assert tally == {"raised_in_any_run": 3, "kept_by_majority": 2}


def test_single_run_is_unchanged():
    kept, tally = majority([[issue("C3", "2 BEER 70,000")]])
    assert len(kept) == 1 and kept[0]["evidence"]["votes"] == "1/1"
