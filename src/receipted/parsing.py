"""Turn the messy strings in CORD ground truth into numbers.

CORD receipts are Indonesian, so prices are Rupiah with no cents. The dataset keeps the
text exactly as printed, which means we see all of these for the same idea:
    "16,500"   "16.500"   "35000.00"   "45,000.00"   "9.500,00"   "Rp 58000.00"   "@16,500"
and quantities like:
    "1"   "x2"   "2 x"   "1Prs"   "1.00"   "*2"   "170"

Keeping this in one small module means the same rules are used everywhere and can be unit tested.
"""

import re

Number = int | float


def _first(text):
    """CORD stores a value printed twice as a list, e.g. ["46.636", "46.636"]. Use the first one."""
    if isinstance(text, list):
        for part in text:
            if part not in (None, ""):
                return part
        return None
    return text


def parse_price(text) -> Number | None:
    """Parse a price string into a number. Returns None if there is nothing to parse.

    Rules, in order:
      1. Strip currency words and decorations: "Rp", "IDR", "@", "*", spaces.
      2. "1,500" / "1.500" / "1,234,567"  -> separators followed by exactly 3 digits are
         thousands separators -> 1500, 1500, 1234567.
      3. "35000.00" / "45,000.00" / "9.500,00" -> a final separator followed by 1-2 digits is a
         decimal point; any earlier separators are thousands -> 35000, 45000, 9500.
      4. Anything else: keep only the digits (a last resort, so odd strings still give a number).
    Whole-number results are returned as int so JSON stays clean.
    """
    text = _first(text)
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None

    negative = s.startswith("-") or s.startswith("(")
    s = re.sub(r"(?i)rp\.?|idr|[@*\s()\-]", "", s)
    if not s:
        return None

    if re.fullmatch(r"\d+(?:[.,]\d{3})*", s):
        value: float = float(re.sub(r"[.,]", "", s))
    else:
        m = re.fullmatch(r"(\d+(?:[.,]\d{3})*)[.,](\d{1,2})", s)
        if m:
            whole = int(re.sub(r"[.,]", "", m.group(1)))
            value = whole + int(m.group(2)) / 10 ** len(m.group(2))
        else:
            digits = re.sub(r"\D", "", s)
            if not digits:
                return None
            value = float(digits)

    if negative:
        value = -value
    return int(value) if value.is_integer() else round(value, 2)


def parse_qty(text) -> Number | None:
    """Parse a quantity string: take the first number in it, ignoring 'x', units like 'Prs', etc."""
    text = _first(text)
    if text is None:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", str(text))
    if not m:
        return None
    value = float(m.group().replace(",", "."))
    return int(value) if value.is_integer() else value
