"""Confidence intervals. With only 100 test receipts a single percentage hides a lot of uncertainty.

Two kinds are used:
- wilson_ci for plain proportions (caught / not caught, right / wrong). The Wilson score interval stays honest at
  the edges: 10 of 10 gives 72–100%, not the 100–100% a bootstrap returns when every resample is identical.
- bootstrap_ci for statistics that are not a simple proportion (item F1), by resampling the receipts.
"""

import math
import random


def wilson_ci(successes, n, level=0.95):
    """Wilson score interval for a proportion. Returns (point, low, high) or (None, None, None) if n is 0."""
    if not n:
        return None, None, None
    z = 1.959963984540054 if level == 0.95 else 2.5758293035489004
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def bootstrap_ci(values, statistic=None, n_boot=4000, seed=0, level=0.95):
    """values: a list of per-item numbers (e.g. 1/0 for caught/not). statistic: function of a list -> float,
    default mean. Returns (point_estimate, low, high) or (None, None, None) if values is empty."""
    if not values:
        return None, None, None
    stat = statistic or (lambda xs: sum(xs) / len(xs))
    rng = random.Random(seed)
    n = len(values)
    draws = sorted(stat([values[rng.randrange(n)] for _ in range(n)]) for _ in range(n_boot))
    lo = draws[int((1 - level) / 2 * n_boot)]
    hi = draws[int((1 + level) / 2 * n_boot) - 1]
    return stat(values), lo, hi


def fmt_ci(point, lo, hi, pct=True):
    if point is None:
        return "n/a"
    if pct:
        return f"{point * 100:.0f}% (95% CI {lo * 100:.0f}–{hi * 100:.0f}%)"
    return f"{point:.2f} ({lo:.2f}–{hi:.2f})"
