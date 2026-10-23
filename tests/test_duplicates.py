from receipted.duplicates import duplicate_issue, find_duplicate, register

RECEIPT = {"items": [{"name": "Nasi Goreng"}, {"name": "Es Teh Manis"}], "total": 35000}


def test_exact_and_likely_duplicates(tmp_path):
    reg = tmp_path / "registry.json"
    assert find_duplicate("abc", RECEIPT, path=reg) is None
    register("CLAIM-1", "abc", RECEIPT, "approve", path=reg)

    same_photo = find_duplicate("abc", {"items": [], "total": 1}, path=reg)
    assert same_photo and same_photo["claim_id"] == "CLAIM-1" and "same receipt image" in same_photo["reason"]

    other_photo = {"items": [{"name": "NASI GORENG"}, {"name": "Es Teh  Manis"}], "total": 35000}
    likely = find_duplicate("different", other_photo, path=reg)
    assert likely and "item names" in likely["reason"]

    different = {"items": [{"name": "Ayam Bakar"}, {"name": "Kopi"}], "total": 35000}
    assert find_duplicate("different", different, path=reg) is None
    assert find_duplicate("abc", RECEIPT, claim_id="CLAIM-1", path=reg) is None  # a re-run of the same claim


def test_rejected_claims_are_not_registered(tmp_path):
    reg = tmp_path / "registry.json"
    register("CLAIM-2", "xyz", RECEIPT, "reject", path=reg)
    assert find_duplicate("xyz", RECEIPT, path=reg) is None


def test_issue_cites_clause_c9():
    i = duplicate_issue({"claim_id": "CLAIM-1", "decision": "approve", "registered_at": "t", "reason": "r"})
    assert i["clause_id"] == "C9" and i["severity"] == "high" and i["source"] == "maths"
