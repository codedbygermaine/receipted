"""The claim-form parser is pure Python; test it without Streamlit by extracting the function source."""
import ast
import textwrap
from pathlib import Path

src = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
tree = ast.parse(src.read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "parse_items")
ns = {}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "parse_items", "exec"), ns)
parse_items = ns["parse_items"]


def test_names_with_commas_and_currency_symbols():
    items, problems = parse_items("Chicken, grilled, 1, 10.50\nTeh Es, 2, S$3.00\nSandwich, 6.00\nJust a name")
    assert problems == []
    assert items[0] == {"name": "Chicken, grilled", "qty": 1, "line_total": 10.5}
    assert items[1] == {"name": "Teh Es", "qty": 2, "line_total": 3}
    assert items[2] == {"name": "Sandwich", "qty": 1, "line_total": 6}
    assert items[3] == {"name": "Just a name", "qty": 1, "line_total": None}


def test_bad_lines_are_reported_not_raised():
    items, problems = parse_items("Kopi, 0, 1.80\n, 1, 2\n")
    assert any("quantity" in p for p in problems) and any("no item name" in p for p in problems)
