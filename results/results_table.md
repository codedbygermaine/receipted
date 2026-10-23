## Results (test split)

### Extraction vs CORD ground truth

| model | receipts | item F1 (95% CI) | item precision | item recall | total correct | subtotal correct | tax correct | mean latency | mean cost / receipt |
|---|---|---|---|---|---|---|---|---|---|
| `claude-haiku-5-5` | 100 | 0.92 (0.87–0.95) | 0.88 | 0.95 | 97% | 96% | 97% | 3.68s | $0.0006 |
| `claude-opus-5-5` | 100 | 0.92 (0.88–0.95) | 0.88 | 0.95 | 97% | 98% | 100% | 4.13s | $0.0186 |

### Checks: full agent on 100 test claims with planted errors (`claude-haiku-5-5`)

| planted error | n | caught | recall (95% CI) |
|---|---|---|---|
| inflated amount | 10 | 10 | 100% (95% CI 100–100%) |
| wrong quantity | 10 | 8 | 80% (95% CI 50–100%) |
| item not on receipt | 10 | 10 | 100% (95% CI 100–100%) |
| totals mismatch | 10 | 10 | 100% (95% CI 100–100%) |
| policy breach | 10 | 10 | 100% (95% CI 100–100%) |
| **all planted errors** | 50 | 48 | **96% (95% CI 90–100%)** |

| natural breach (from ground truth) | n | caught | recall |
|---|---|---|---|
| price above list | 3 | 3 | 100% |
| above 500k | 3 | 1 | 33% |
| packaging over 5000 | 2 | 0 | 0% |
| receipt inconsistent | 9 | 3 | 33% |

| metric | value |
|---|---|
| decision accuracy (approve / needs_review / reject) | 83% (95% CI 76–90%) |
| clean claims (no planted error, no natural breach) | 41 |
| false alarms: clean claim flagged with an issue | 8 (20% (95% CI 7–32%)) |
| clean claims held only because the receipt was hard to read | 6 |
| rule-check issues raised / dropped by verifier | 48 / 4 |
| mean cost per claim | $0.0013 |
| mean seconds per claim (uncached) | 4.82 |

### Run 1 vs run 2 (same test claims, before and after the fixes from the error analysis)

| metric | run 1 | run 2 |
|---|---|---|
| planted errors caught | 47/50 | 48/50 |
| decision accuracy | 81% | 83% |
| false alarms (clean claims flagged) | 10/41 | 8/41 |
| rule-check issues dropped by verifier | 1 | 4 |
| mean cost per claim | $0.0013 | $0.0013 |

Run 2 is reported because the three fixes were motivated by failures seen in run 1; both are kept so the effect is visible and the second run is not mistaken for a first.

### Drafts: LLM-as-judge (`claude-opus-5-5` scoring `claude-haiku-5-5` drafts, 1–5)

| accuracy | evidence | clarity | tone | drafts with accuracy < 4 |
|---|---|---|---|---|
| 4.6 | 4.89 | 4.73 | 4.98 | 4 / 100 |

| human vs judge (10 drafts) | exact agreement | within 1 point |
|---|---|---|
| accuracy | 80% | 100% |
| evidence | 90% | 100% |
| clarity | 70% | 90% |
| tone | 100% | 100% |
