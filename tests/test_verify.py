from receipted.verify import verify

CLAUSES = {"C3": {"id": "C3", "title": "Alcohol", "text": "No alcohol."},
           "C7": {"id": "C7", "title": "Two approvers", "text": "Above 500,000 needs two approvers."}}
PRICES = {"iced tea": {"item": "iced tea", "agreed_max_unit_price": 13500}}
RECEIPT = {"items": [
    {"name": "Bir Bintang", "qty": 2, "unit_price": 35000, "line_total": 70000, "raw_line": "2 BIR BINTANG 70,000"},
    {"name": "Iced Tea", "qty": 1, "unit_price": None, "line_total": 20000, "raw_line": "1 ICED TEA 20,000"},
]}


def rule(**kw):
    base = {"source": "rules", "type": "x", "severity": "high", "message": "", "receipt_line": None,
            "clause_id": None, "price_item": None, "evidence": {}}
    return {**base, **kw}


def test_good_citation_is_kept_with_clause_text():
    kept, dropped = verify([rule(clause_id="C3", receipt_line="2 BIR BINTANG 70,000")], RECEIPT, CLAUSES, PRICES)
    assert len(kept) == 1 and dropped == []
    assert kept[0]["evidence"]["clause_text"].startswith("C3.")


def test_unknown_clause_is_dropped():
    kept, dropped = verify([rule(clause_id="C99", receipt_line="2 BIR BINTANG 70,000")], RECEIPT, CLAUSES, PRICES)
    assert kept == [] and dropped[0]["dropped_because"].startswith("cited clause")


def test_line_not_in_extraction_is_dropped():
    kept, dropped = verify([rule(clause_id="C3", receipt_line="1 VODKA 90,000")], RECEIPT, CLAUSES, PRICES)
    assert kept == [] and "receipt line" in dropped[0]["dropped_because"]


def test_whitespace_and_case_differences_are_tolerated():
    kept, _ = verify([rule(clause_id="C3", receipt_line="  2  bir bintang   70,000 ")], RECEIPT, CLAUSES, PRICES)
    assert len(kept) == 1


def test_anchor_lines_are_allowed_for_whole_claim_rules():
    kept, _ = verify([rule(clause_id="C7", receipt_line="CLAIM_AMOUNT")], RECEIPT, CLAUSES, PRICES)
    assert len(kept) == 1


def test_price_issue_needs_a_matching_product_name():
    cake = {**RECEIPT, "items": [{"name": "BANABERRY FRESH CREAM CAK", "qty": 1, "unit_price": None,
                                 "line_total": 230000, "raw_line": "1 BANABERRY FRESH CREAM CAK 230,000"}]}
    prices = {"almond cream cheese": {"item": "almond cream cheese", "agreed_max_unit_price": 31000}}
    wrong = rule(price_item="almond cream cheese", receipt_line="1 BANABERRY FRESH CREAM CAK 230,000")
    kept, dropped = verify([wrong], cake, CLAUSES, prices)
    assert kept == [] and "does not look like" in dropped[0]["dropped_because"]
    # word order and case differences are still the same product
    teh = {**RECEIPT, "items": [{"name": "Teh Es", "qty": 1, "unit_price": None, "line_total": 7000, "raw_line": "1 Teh Es 7.000"}]}
    prices = {"es teh": {"item": "es teh", "agreed_max_unit_price": 6500}}
    kept, dropped = verify([rule(price_item="es teh", receipt_line="1 Teh Es 7.000")], teh, CLAUSES, prices)
    assert len(kept) == 1 and kept[0]["evidence"]["price_name_similarity"] >= 65


def test_price_issue_is_rechecked_numerically():
    above = rule(price_item="iced tea", receipt_line="1 ICED TEA 20,000")       # 20000 > 13500: keep
    kept, dropped = verify([above], RECEIPT, CLAUSES, PRICES)
    assert len(kept) == 1 and kept[0]["evidence"]["agreed_max_unit_price"] == 13500
    cheap = {**RECEIPT, "items": [{**RECEIPT["items"][1], "line_total": 12000}]}
    kept, dropped = verify([above], cheap, CLAUSES, PRICES)                     # 12000 <= 13500: drop
    assert kept == [] and "not above" in dropped[0]["dropped_because"]


def test_maths_issues_pass_through():
    m = {"source": "maths", "type": "claim_exceeds_receipt", "severity": "high", "message": "", "receipt_line": None,
         "clause_id": None, "price_item": None, "evidence": {"claimed": 1, "receipt_total": 0}}
    kept, dropped = verify([m], RECEIPT, CLAUSES, PRICES)
    assert kept == [m] and dropped == []


def test_clause_issue_that_also_names_a_price_row_is_not_price_checked():
    # a C3 (alcohol) issue on a line whose price is under the agreed max must survive
    prices = {"bir bintang": {"item": "bir bintang", "agreed_max_unit_price": 40000}}
    i = rule(clause_id="C3", price_item="bir bintang", receipt_line="2 BIR BINTANG 70,000")
    kept, dropped = verify([i], RECEIPT, CLAUSES, prices)
    assert len(kept) == 1 and dropped == [] and kept[0]["evidence"]["price_list_item"] == "bir bintang"
