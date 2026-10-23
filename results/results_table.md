## Results (test split)

### Extraction vs CORD ground truth

| model | receipts | item F1 | item precision | item recall | total correct | subtotal correct | tax correct | mean latency | mean cost / receipt |
|---|---|---|---|---|---|---|---|---|---|
| `claude-haiku-5-5` | 100 | 0.92 | 0.88 | 0.95 | 97% | 96% | 97% | 3.68s | $0.0006 |
| `claude-opus-5-5` | 100 | 0.92 | 0.88 | 0.95 | 97% | 98% | 100% | 4.13s | $0.0186 |

### Checks: full agent on 100 synthetic claims (`claude-haiku-5-5`)

| planted error | n | caught | recall |
|---|---|---|---|
| inflated amount | 10 | 10 | 100% |
| wrong quantity | 10 | 8 | 80% |
| item not on receipt | 10 | 10 | 100% |
| totals mismatch | 10 | 10 | 100% |
| policy breach | 10 | 9 | 90% |

| natural breach (from ground truth) | n | caught | recall |
|---|---|---|---|
| price above list | 3 | 3 | 100% |
| above 500k | 3 | 1 | 33% |
| packaging over 5000 | 2 | 0 | 0% |
| receipt inconsistent | 9 | 3 | 33% |

| metric | value |
|---|---|
| decision accuracy (approve / needs_review / reject) | 81% |
| clean claims (no planted error, no natural breach) | 41 |
| false alarms: clean claim flagged with an issue | 10 (24%) |
| clean claims held only because the receipt was hard to read | 5 |
| rule-check issues raised / dropped by verifier | 56 / 1 |
| mean cost per claim | $0.0013 |
| mean seconds per claim (uncached) | 6.22 |
