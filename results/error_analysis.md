# Error analysis (test split, claude-haiku-5-5)

> Written from **run 1**. The three fixes it motivated (cases 1, 2 and 3) were then applied and the test claims re-run once as run 2: TES-097 is no longer rejected (held for readability instead), TES-011's wrong-product price match is dropped by the verifier, and TES-032's missing purpose is caught. Both runs are in `results/` and compared in the README.

Five real failures, picked from the worst cases in `checks_test_claude-haiku-5-5.json` and `extraction_test_*.json`. Image ids refer to `data/images/test/`.

## 1. A false reject from whitespace in a name (TES-097, test_097)
The claim listed `SATE ATI GO`, copied from the ground truth. The model read the printed line as `SATECATIGO` (the receipt's spacing is poor). The fuzzy name matcher scored the pair at 48 out of 100, below the 70 threshold, so the deterministic check raised "claimed item not on receipt" (high severity) and the claim was rejected. **Why:** `rapidfuzz.token_set_ratio` depends on token boundaries, and this receipt has none. **Fix:** also compare the names with all spaces removed, and treat a high score on either form as a match.

## 2. A price-list row matched to the wrong product (TES-011, test_011; also TES-000)
A 230,000 rupiah cake (`BANABERRY FRESH CREAM CAK`) was flagged as above the agreed maximum for `almond cream cheese` (31,000). On test_000 a cinema ticket was compared with a price row called `dept01`. **Why:** retrieval returns the three nearest price rows for every item, and the rule check sometimes treats the nearest row as the same product. The verifier confirms the row exists and that the number comparison holds, but it does not check that the row *is* that product. This is the largest source of false alarms (6 of the 10 flagged clean claims cite a price row; at least 2 of those 6 are clearly the wrong product). **Fix:** a name-similarity guard in the verifier: drop a price issue unless the price-list item and the receipt item names are close, and show the match score as evidence.

## 3. A missing purpose that went unflagged (TES-032, test_032)
The planted breach was an empty purpose (clause C1). Nine of ten such claims were caught after the retrieval query and rule prompt were changed on the validation split to say "purpose: NOT STATED"; this one was not, and the claim was approved. **Why:** the rule check is a model call, and a model applies a rule most of the time, not every time. **Fix:** "purpose is empty" is a one-line deterministic check; it belongs in `maths.py` beside the other code checks, with the LLM reserved for judgements code cannot make.

## 4. A missed tax line turning into a false alarm (TES-013, test_013)
Extraction returned `tax: null` for a receipt that prints a 10% tax of 4,664 (the ground truth stores it as a list, meaning it was printed twice). With no tax, subtotal 46,636 did not reach the total 51,300, so the arithmetic check flagged it and the clean claim was held for review. **Why:** an extraction miss on a summary line looks exactly like a receipt that does not add up. The human-review route caught it, which is the design, but it cost a reviewer a look. **Fix:** when the gap between subtotal and total is close to 10% or 11% of the subtotal and tax is null, say "tax line probably not read" rather than "totals do not add up", and route the same way.

## 5. A wrong quantity caught for the wrong reason (TES-001, test_001; also TES-068)
The planted error was one extra unit of `Y.B.BAT`. The agent rejected the claim, correctly, but only as "claim exceeds receipt total"; it never said which item's quantity was wrong. **Why:** the extracted item either had no quantity (the model left `qty` empty even though the raw line started with a number, as on test_055) or its name did not match the claim's name, so the quantity comparison never ran. The decision was right, the explanation was incomplete, and the strict per-kind metric counts it as a miss.

## What the false-alarm number means
10 of 41 clean claims were flagged with an issue (24%). Reading those 10: at least 3 are correct by the policy as written and were missed by the synthetic labels, not by the agent: a women's blouse (`BLUS WANITA`, clause C6, test_012), a 377,859 dinner claimed for 2 people (above the 150,000 per-person cap in C12, test_020), and `Teh Es` at 7,000 against the `es teh` row's 6,500 (test_085). The labels match price-list rows by strict string similarity; the model matches by meaning, which is sometimes right (Teh Es) and sometimes wrong (dept01). Two more are extraction slips (cases 2 and 4 above) and one is a ground-truth quantity that disagrees with what the receipt prints (test_063). The remaining alarms are the wrong-product matches in case 2. So 24% is an upper bound; the genuinely wrong flags are closer to 4 or 5 of 41.

## Extraction misses worth knowing (both models)
- Zero-priced bundle lines (`PAKET SLICES 0`) are listed by the model and omitted by CORD. They do no harm to the maths but cost item precision (test_099, test_016).
- A "Sub Total" line with no "Total" line is labelled as the total in CORD; the model reports it as the subtotal (test_018, test_071). Both are defensible.
- A trailing "1" printed after the item name is folded into the name (test_018).
- One quantity left blank although the raw line starts with "2" (test_055). A real slip, on a clear image.
- One blurry `Tetes` read as `Tefes` (test_071).

## Seen in the live demo (25 Oct 2026): a misspelling in a reply

A reply drafted by Haiku 5.5 for a held claim opened with "Your claym API-… is on hold for review". One occurrence in the demo so far, none found in the cached evaluation drafts (`grep claym data/cache` is empty), and the judge never saw it, so the reply-quality scores stand. The draft is written by the model end to end; a fixed, templated opening sentence would remove this class of error but would also change the output the judge scored, so it is left as it is and recorded here as a known risk. If it recurs, the fix is a templated first line plus a spell check on the draft before it is shown.
