from receipted.maths import check_claim, check_receipt, close


def item(name, qty=1, unit=None, total=None, raw=None, discount=None):
    return {"name": name, "qty": qty, "unit_price": unit, "line_total": total,
            "raw_line": raw or f"{qty} {name} {total}", "discount": discount}


def receipt(items, subtotal=None, tax=None, service=None, discount=None, total=None):
    return {"items": items, "subtotal": subtotal, "tax": tax, "service": service,
            "discount": discount, "total": total}


def types(issues):
    return sorted(i["type"] for i in issues)


def test_close_tolerates_rounding_to_thousand():
    assert close(29972, 30000)       # 0.09% off
    assert not close(29000, 30000)   # 3.3% off
    assert close(5, 6) and not close(5, 7)


def test_clean_receipt_has_no_issues():
    r = receipt([item("A", 2, 10000, 20000), item("B", 1, 5000, 5000)], subtotal=25000, tax=2500, total=27500)
    assert check_receipt(r) == []


def test_line_arithmetic_error_cites_the_line():
    r = receipt([item("A", 2, 10000, 25000, raw="2 A 25,000")], subtotal=25000, total=25000)
    issues = check_receipt(r)
    assert types(issues) == ["line_arithmetic"]
    assert issues[0]["receipt_line"] == "2 A 25,000"
    assert issues[0]["evidence"]["expected"] == 20000


def test_lines_not_matching_subtotal():
    r = receipt([item("A", 1, None, 10000), item("B", 1, None, 10000)], subtotal=25000, total=25000)
    assert types(check_receipt(r)) == ["lines_vs_totals"]


def test_tax_inclusive_receipt_is_accepted():
    # lines sum to the total, subtotal is the ex-tax figure: a real CORD pattern
    r = receipt([item("A", 1, None, 20000)], subtotal=18181, tax=1818, total=20000)
    assert check_receipt(r) == []


def test_item_discounts_count_towards_subtotal():
    r = receipt([item("A", 1, None, 19500, discount=-7800)], subtotal=11700, total=11700)
    assert check_receipt(r) == []


def test_totals_arithmetic_error():
    r = receipt([item("A", 1, None, 10000)], subtotal=10000, tax=1000, service=500, total=12000)
    assert types(check_receipt(r)) == ["totals_arithmetic"]


def test_empty_receipt():
    assert types(check_receipt(receipt([]))) == ["no_line_items"]


def test_claim_matches_receipt():
    r = receipt([item("Nasi Goreng", 2, 25000, 50000)], total=50000)
    c = {"amount": 50000, "items": [{"name": "nasi goreng", "qty": 2, "line_total": 50000}]}
    assert check_claim(c, r) == []


def test_inflated_claim_is_high_severity():
    r = receipt([item("A", 1, None, 50000)], total=50000)
    issues = check_claim({"amount": 80000, "items": []}, r)
    assert types(issues) == ["claim_exceeds_receipt"]
    assert issues[0]["severity"] == "high"
    assert issues[0]["evidence"]["difference"] == 30000


def test_underclaim_is_low_severity():
    r = receipt([item("A", 1, None, 50000)], total=50000)
    issues = check_claim({"amount": 40000, "items": []}, r)
    assert types(issues) == ["claim_below_receipt"] and issues[0]["severity"] == "low"


def test_claimed_item_not_on_receipt():
    r = receipt([item("Es Teh Tawar", 1, None, 7000)], total=7000)
    issues = check_claim({"amount": 7000, "items": [{"name": "Bir Bintang", "qty": 1}]}, r)
    assert types(issues) == ["claimed_item_not_on_receipt"]


def test_claimed_qty_above_receipt():
    r = receipt([item("Egg Tart", 1, None, 13000, raw="1 EGG TART 13,000")], total=13000)
    issues = check_claim({"amount": 13000, "items": [{"name": "egg tart", "qty": 3}]}, r)
    assert types(issues) == ["claimed_qty_exceeds_receipt"]
    assert issues[0]["receipt_line"] == "1 EGG TART 13,000"


def test_claim_lines_must_sum_to_amount():
    r = receipt([item("A", 1, None, 10000), item("B", 1, None, 5000)], total=15000)
    c = {"amount": 15000, "items": [{"name": "A", "qty": 1, "line_total": 10000},
                                    {"name": "B", "qty": 1, "line_total": 2000}]}
    assert types(check_claim(c, r)) == ["claim_lines_vs_amount"]
