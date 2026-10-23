# Human scoring sheet (test) — score 1-5 per dimension using the rubric below

Score each message against the facts shown for it: the claim facts (amount, receipt total, decision) AND the verified issues. A message may state any of those; it must not add problems or numbers that are not there.

Score each dimension from 1 to 5.

ACCURACY — does the message state only what the verified issues and decision say?
 5: every number, item, clause id and the decision match the facts exactly; nothing added.
 3: one small slip (a rounded number, a clause id missing) but no invented problem.
 1: states a problem or fact that is not in the verified issues, or gets the decision wrong.

EVIDENCE — does each problem mentioned point at its evidence?
 5: each problem gives the numbers involved (claimed vs receipt, qty, price) and the clause id or receipt line.
 3: problems are named but some evidence (a number or clause) is left out.
 1: problems are asserted with no numbers or clauses, or evidence is mismatched to the wrong problem.

CLARITY — could the member act on it without asking a question?
 5: each problem is one clear point with what to do next; no duplication; under about 150 words.
 3: understandable but repetitive, vague on next steps, or overly long.
 1: confusing, contradictory, or the required action is unclear.

TONE — polite, neutral, treasurer-to-member.
 5: courteous and matter-of-fact; no accusation, no apology spiral, no jargon.
 3: slightly stiff or slightly too casual, or one awkward phrase.
 1: accusatory, sarcastic, or inappropriate.

---

## TES-032  (decision: needs_review)

**Claim facts the writer was given:** submitter Member 032, claimed amount 24000 IDR, receipt total 24000, decision needs_review (medium-severity issues need a human decision).

**Verified issues (the only problems the message may mention):**

- [medium] purpose_missing (C1): No purpose is stated on the claim; policy C1 requires one  
  receipt line: `CLAIM_AMOUNT`  
  evidence: {'purpose': ''}

**Message:**

> Dear Member 032,
> 
> Thank you for submitting claim TES-032. Your claim for IDR 24,000 matches the receipt total, but it is currently on hold.
> 
> The reason is that no purpose is stated on the claim, and policy C1 requires one. To release the claim, please reply with a short description of what the expense was for, and we will review it again.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## TES-033  (decision: needs_review)

**Claim facts the writer was given:** submitter Member 033, claimed amount 148127 IDR, receipt total 148127, decision needs_review (medium-severity issues need a human decision).

**Verified issues (the only problems the message may mention):**

- [medium] lines_vs_totals (code): Line items sum to 184500, but subtotal is 117500 and total is 148127  
  evidence: {'line_sum': 184500, 'subtotal': 117500, 'total': 148127}
- [medium] totals_arithmetic (code): 117500 + tax 19557 + service 11070 - discount 67000 = 81127, but total shows 148127  
  evidence: {'subtotal': 117500, 'tax': 19557, 'service': 11070, 'discount': 67000, 'expected': 81127, 'total': 148127}
- [medium] claim_lines_vs_amount (code): Claim lines sum to 220500 but the claimed amount is 148127 (receipt tax + service = -36373)  
  evidence: {'claim_line_sum': 220500, 'claimed': 148127, 'receipt_tax_and_service': -36373}

**Message:**

> Subject: Expense claim TES-033 is on hold
> 
> Dear Member 033,
> 
> Your claim TES-033 for IDR 148,127 is on hold while we review it. We found three problems that need a human decision:
> 
> - The line items add up to IDR 184,500, but the receipt subtotal is IDR 117,500 and the total is IDR 148,127.
> - The receipt does not add up: 117,500 + tax 19,557 + service 11,070 - discount 67,000 = 81,127, but the total shows 148,127.
> - Your claim lines add up to IDR 220,500, but the claimed amount is IDR 148,127. The receipt tax and service come to -36,373.
> 
> You can help by sending a corrected or clearer receipt, or by explaining how the claim lines relate to the receipt amount. We will confirm once the review is complete.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## TES-099  (decision: approve)

**Claim facts the writer was given:** submitter Member 099, claimed amount 75000 IDR, receipt total 75000, decision approve (no issues found and the receipt is clear).

**Verified issues (the only problems the message may mention):**

- none

**Message:**

> Hello Member 099,
> 
> Your expense claim TES-099 for IDR 75,000 has been approved and will be paid. The amount you claimed matches the receipt total of IDR 75,000, and no issues were found.
> 
> Thank you for submitting your claim.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## TES-025  (decision: reject)

**Claim facts the writer was given:** submitter Member 025, claimed amount 65000 IDR, receipt total 43000, decision reject (at least one high-severity issue with evidence).

**Verified issues (the only problems the message may mention):**

- [high] claim_exceeds_receipt (code): Claimed 65000 but the receipt total is 43000  
  evidence: {'claimed': 65000, 'receipt_total': 43000, 'difference': 22000}
- [high] claimed_item_not_on_receipt (code): 'A.MINERAL BOTOL' is claimed but no receipt line matches it  
  evidence: {'claimed_name': 'A.MINERAL BOTOL', 'closest': 'POTATO PEPPER BAGEL', 'match_score': 41.1764705882353}

**Message:**

> Dear Member 025,
> 
> Thank you for submitting claim TES-025. We are unable to pay this claim as submitted, and it has been rejected.
> 
> - The claimed amount is 65,000 IDR, but the receipt total is 43,000 IDR, a difference of 22,000 IDR.
> - The item "A.MINERAL BOTOL" is claimed, but no matching line appears on the receipt.
> 
> To have this claim reconsidered, please correct the claimed amount to match the receipt total, or provide a receipt that includes the mineral water item. You are welcome to resubmit with these changes.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## TES-068  (decision: reject)

**Claim facts the writer was given:** submitter Member 068, claimed amount 60000 IDR, receipt total 20000, decision reject (at least one high-severity issue with evidence).

**Verified issues (the only problems the message may mention):**

- [high] claim_exceeds_receipt (code): Claimed 60000 but the receipt total is 20000  
  evidence: {'claimed': 60000, 'receipt_total': 20000, 'difference': 40000}

**Message:**

> Hello Member 068,
> 
> We have reviewed expense claim TES-068 and it cannot be paid as submitted. You claimed IDR 60,000, but the receipt total is IDR 20,000, a difference of IDR 40,000.
> 
> To have this claim considered, please submit a claim for IDR 20,000 that matches the receipt, or send a corrected receipt that supports the full IDR 60,000.
> 
> Thank you,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## TES-045  (decision: reject)

**Claim facts the writer was given:** submitter Member 045, claimed amount 103000 IDR, receipt total 88000, decision reject (at least one high-severity issue with evidence).

**Verified issues (the only problems the message may mention):**

- [high] claim_exceeds_receipt (code): Claimed 103000 but the receipt total is 88000  
  evidence: {'claimed': 103000, 'receipt_total': 88000, 'difference': 15000}
- [high] claim_above_receipt_total (C4): The claim of IDR 103,000 exceeds the receipt total of IDR 88,000, so under C4 the claim is rejected as submitted. The claimant should resubmit for no more than IDR 88,000.  
  receipt line: `CLAIM_AMOUNT`
- [medium] price_above_list (roti): The receipt shows IDR 7,000 for Roti Keju Manis, but the agreed maximum for the matching price-list row 'roti' is IDR 5,500. The treasurer should confirm the item or hold the excess for review.  
  receipt line: `1 Roti Keju Manis. 7.000`  
  evidence: {'price_name_similarity': 100, 'unit_price_paid': 7000.0, 'agreed_max_unit_price': 5500, 'price_list_item': 'roti'}

**Message:**

> Subject: Expense claim TES-045 - not paid as submitted
> 
> Hello Member 045,
> 
> Your claim TES-045 cannot be paid as submitted. You claimed IDR 103,000, but the receipt total is IDR 88,000, a difference of IDR 15,000. Under clause C4, a claim cannot be higher than the receipt total.
> 
> To fix this, please resubmit the claim for no more than IDR 88,000.
> 
> Also, the receipt shows IDR 7,000 for Roti Keju Manis, while the agreed maximum price for roti is IDR 5,500. Please check this item when you resubmit. If you paid the higher price, the treasurer will need to confirm it before any excess is paid.
> 
> Thank you,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## TES-030  (decision: needs_review)

**Claim facts the writer was given:** submitter Member 030, claimed amount 31500 IDR, receipt total 31500, decision needs_review (medium-severity issues need a human decision).

**Verified issues (the only problems the message may mention):**

- [medium] purpose_missing (C1): No purpose is stated on the claim; policy C1 requires one  
  receipt line: `CLAIM_AMOUNT`  
  evidence: {'purpose': ''}

**Message:**

> Hello Member 030,
> 
> Your expense claim TES-030 for IDR 31,500 is on hold for review. The receipt total matches the claimed amount, but no purpose is stated on the claim, and policy C1 requires one.
> 
> To move this forward, please reply with a short description of what the expense was for. Once we have it, the claim will be looked at again.
> 
> Thank you,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## TES-073  (decision: needs_review)

**Claim facts the writer was given:** submitter Member 073, claimed amount 22000 IDR, receipt total 22000, decision needs_review (medium-severity issues need a human decision).

**Verified issues (the only problems the message may mention):**

- [medium] claim_lines_vs_amount (code): Claim lines sum to 24000 but the claimed amount is 22000  
  evidence: {'claim_line_sum': 24000, 'claimed': 22000, 'receipt_tax_and_service': 0}

**Message:**

> Dear Member 073,
> 
> Your expense claim TES-073 is on hold while a committee member reviews it.
> 
> The claim lines add up to IDR 24,000, but the claimed amount is IDR 22,000. The receipt total is IDR 22,000, and it shows no tax or service charge.
> 
> Please check the individual claim lines and the claimed amount. If the lines are correct, let us know which figure should be used, or send a corrected claim with matching totals. Once the difference is resolved, the claim will be reviewed again.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## TES-046  (decision: reject)

**Claim facts the writer was given:** submitter Member 046, claimed amount 85000 IDR, receipt total 40000, decision reject (at least one high-severity issue with evidence).

**Verified issues (the only problems the message may mention):**

- [high] claim_exceeds_receipt (code): Claimed 85000 but the receipt total is 40000  
  evidence: {'claimed': 85000, 'receipt_total': 40000, 'difference': 45000}
- [high] claimed_item_not_on_receipt (code): 'CHANGE TO CHICKEN BOX' is claimed but no receipt line matches it  
  evidence: {'claimed_name': 'CHANGE TO CHICKEN BOX', 'closest': 'S-Caramel Milk Tea', 'match_score': 35.29411764705882}

**Message:**

> Dear Member 046,
> 
> Thank you for submitting claim TES-046. We cannot pay it as submitted, so it has been rejected.
> 
> - The claimed amount is 85000 IDR, but the receipt total is 40000 IDR. The difference is 45000 IDR.
> - The item "CHANGE TO CHICKEN BOX" is claimed, but no matching line appears on the receipt.
> 
> To have this claim reconsidered, please submit a claim for no more than the receipt total of 40000 IDR, and make sure every claimed item appears on the receipt. If the item was purchased, please provide a receipt that shows it.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## TES-002  (decision: reject)

**Claim facts the writer was given:** submitter Member 002, claimed amount 76000 IDR, receipt total 28000, decision reject (at least one high-severity issue with evidence).

**Verified issues (the only problems the message may mention):**

- [high] claim_exceeds_receipt (code): Claimed 76000 but the receipt total is 28000  
  evidence: {'claimed': 76000, 'receipt_total': 28000, 'difference': 48000}
- [medium] claim_lines_vs_amount (code): Claim lines sum to 72000 but the claimed amount is 76000  
  evidence: {'claim_line_sum': 72000, 'claimed': 76000, 'receipt_tax_and_service': 0}
- [high] claimed_qty_exceeds_receipt (code): Claimed 3 x 'JASMINE MT ( L )' but the receipt shows 1  
  receipt line: `1 JASMINE MT (L) 24,000`  
  evidence: {'claimed_qty': 3, 'receipt_qty': 1, 'receipt_item': 'JASMINE MT (L)'}
- [high] claim_exceeds_receipt_policy (C4): The claimed amount of 76000 is more than the receipt total of 28000, so C4 requires the claim to be rejected. Reduce the claim to the receipt total or less.  
  receipt line: `CLAIM_AMOUNT`
- [high] claimed_qty_exceeds_receipt_policy (C9): The claim asks for 3 units of JASMINE MT but the receipt shows only 1, which C9 does not allow. Claim no more than the receipt quantity.  
  receipt line: `1 JASMINE MT (L) 24,000`

**Message:**

> Subject: Expense claim TES-002 - cannot be paid as submitted
> 
> Dear Member 002,
> 
> Thank you for submitting claim TES-002. Unfortunately it cannot be paid as submitted, for the following reasons:
> 
> - The claimed amount is 76000 IDR, but the receipt total is 28000 IDR, a difference of 48000 IDR. Under clause C4, a claim for more than the receipt total is rejected.
> - The claim lines add up to 72000 IDR, which does not match the claimed amount of 76000 IDR.
> - You claimed 3 units of JASMINE MT (L), but the receipt shows only 1 (24,000). Under clause C9, the quantity claimed must not exceed the receipt quantity.
> 
> To resubmit, please reduce the claim to 28000 IDR or less, make sure the claim lines match that amount, and claim no more than the quantities shown on the receipt.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---
