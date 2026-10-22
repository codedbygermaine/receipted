import pytest

from receipted.parsing import parse_price, parse_qty


@pytest.mark.parametrize("text, expected", [
    ("16,500", 16500),          # comma thousands
    ("16.500", 16500),          # dot thousands
    ("1,234,567", 1234567),
    ("5", 5),
    ("909", 909),
    ("35000.00", 35000),        # dot decimals, no thousands
    ("45,000.00", 45000),       # comma thousands + dot decimals
    ("9.500,00", 9500),         # dot thousands + comma decimals
    ("12,500.50", 12500.5),
    ("Rp 58000.00", 58000),
    ("Rp.16.500", 16500),
    ("@16,500", 16500),
    ("@ 16.500", 16500),
    ("*12345", 12345),
    ("-5,000", -5000),          # discount
    ("0.00", 0),
    ("", None),
    (None, None),
    ("abc", None),
    (["46.636", "46.636"], 46636),   # value printed twice -> stored as a list
    (["6,818", "0"], 6818),
    ([], None),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("1", 1),
    ("x2", 2),
    ("2x", 2),
    ("2 X", 2),
    ("2 x", 2),
    ("1Prs", 1),
    ("1Gls", 1),
    ("*2", 2),
    ("170", 170),
    ("1.00", 1),
    ("1.5", 1.5),
    ("", None),
    (None, None),
    (["2", "2"], 2),
])
def test_parse_qty(text, expected):
    assert parse_qty(text) == expected
