## Results (validation split)

### Extraction vs CORD ground truth

| model | receipts | item F1 | item precision | item recall | total correct | subtotal correct | tax correct | mean latency | mean cost / receipt |
|---|---|---|---|---|---|---|---|---|---|
| `claude-haiku-5-5` | 10 | 0.94 | 0.88 | 1.00 | 100% | 90% | 100% | 3.43s | $0.0005 |

### Checks: full agent on 10 synthetic claims (`claude-haiku-5-5`)

| planted error | n | caught | recall |
|---|---|---|---|
| inflated amount | 1 | 1 | 100% |
| wrong quantity | 2 | 2 | 100% |
| item not on receipt | 0 | 0 | n/a |
| totals mismatch | 0 | 0 | n/a |
| policy breach | 2 | 2 | 100% |

| natural breach (from ground truth) | n | caught | recall |
|---|---|---|---|
| receipt inconsistent | 2 | 2 | 100% |

| metric | value |
|---|---|
| decision accuracy (approve / needs_review / reject) | 100% |
| clean claims (no planted error, no natural breach) | 3 |
| false alarms: clean claim flagged with an issue | 0 (0%) |
| clean claims held only because the receipt was hard to read | 0 |
| rule-check issues raised / dropped by verifier | 8 / 0 |
| mean cost per claim | $0.0012 |
| mean seconds per claim (uncached) | 5.14 |

### Drafts: LLM-as-judge (`claude-opus-5-5` scoring `claude-haiku-5-5` drafts, 1–5)

| accuracy | evidence | clarity | tone | drafts with accuracy < 4 |
|---|---|---|---|---|
| 5 | 4.9 | 5 | 5 | 0 / 10 |

_Human scoring sheet generated; agreement will be reported once it is filled in._
