"""Bootstrap confidence intervals. With only 100 test receipts a single percentage hides a lot of
uncertainty; resampling the claims with replacement and recomputing the metric a few thousand times
shows how much the number could move on a different 100.
"""

import random


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
