# Human scoring sheet (validation) — score 1-5 per dimension using the rubric below

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

## VAL-004  (decision: approve)

**Verified issues (the only facts the message may use):**

- none

**Message:**

> Hello Member 004,
> 
> Your expense claim VAL-004 for IDR 41,000 has been approved and will be paid. The amount matches your receipt total of IDR 41,000.00, and no issues were found.
> 
> Thank you for submitting your claim.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## VAL-009  (decision: needs_review)

**Verified issues (the only facts the message may use):**

- [medium] purpose_missing (C1): The claim states no purpose, so it is held for review. The treasurer should ask the submitter to state the approved club activity or business purpose before reimbursement.

**Message:**

> Hello Member 009,
> 
> Your expense claim VAL-009 for IDR 20,000 is on hold for review. The claim does not state a purpose. Under clause C1, expenses are reimbursable only when incurred for an approved club activity or business purpose, and the claim must state that purpose.
> 
> To move this forward, please reply with the approved club activity or business purpose for this expense. Once we have it, the claim can be reviewed again.
> 
> Thank you,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## VAL-003  (decision: approve)

**Verified issues (the only facts the message may use):**

- none

**Message:**

> Hello Member 003,
> 
> Your expense claim VAL-003 for IDR 28,000 has been approved and will be paid. The amount matches your receipt total of IDR 28,000.00, and no issues were found.
> 
> Thank you for submitting a clear receipt.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## VAL-008  (decision: needs_review)

**Verified issues (the only facts the message may use):**

- [medium] lines_vs_totals (code): Line items sum to 19500.0, but subtotal is 11700.0 and total is 11700.0
- [medium] claim_lines_vs_amount (code): Claim lines sum to 19500 but the claimed amount is 11700

**Message:**

> Subject: Expense claim VAL-008 is on hold
> 
> Hello Member 008,
> 
> Your claim VAL-008 for IDR 11,700 is on hold while a person reviews it.
> 
> The line items on your receipt add up to IDR 19,500, but the receipt subtotal and total both show IDR 11,700. The claim lines also add up to IDR 19,500, while the claimed amount is IDR 11,700.
> 
> Please check the receipt and your claim lines, then reply with a corrected claim or a note explaining the difference. Once we have that, the claim will be reviewed again.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## VAL-002  (decision: reject)

**Verified issues (the only facts the message may use):**

- [high] claim_exceeds_receipt (code): Claimed 60000 but the receipt total is 20000.0
- [high] claimed_qty_exceeds_receipt (code): Claimed 3 x 'S-Ovaltine 50%' but the receipt shows 1.0
- [high] claim_exceeds_receipt (C4): The claim is IDR 60,000 but the receipt total is IDR 20,000. Under C4 a claim above the receipt total is rejected, so the claim should be reduced to IDR 20,000 or rejected.
- [high] claimed_qty_exceeds_receipt (C9): The claim asks for 3 units of S-Ovaltine 50% but the receipt shows only 1. Under C9 the claimed quantity may not exceed the receipt quantity.

**Message:**

> Dear Member 002,
> 
> Your expense claim VAL-002 cannot be paid as submitted, so it has been rejected.
> 
> - Amount: you claimed IDR 60,000, but the receipt total is IDR 20,000. Under clause C4, a claim above the receipt total is rejected. To fix this, reduce the claim to IDR 20,000 or lower and resubmit.
> - Quantity: you claimed 3 units of S-Ovaltine 50%, but the receipt shows only 1. Under clause C9, the claimed quantity may not exceed the receipt quantity. To fix this, claim only 1 unit.
> 
> Please correct both points and resubmit the claim.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## VAL-001  (decision: reject)

**Verified issues (the only facts the message may use):**

- [high] claim_exceeds_receipt (code): Claimed 46000 but the receipt total is 23000.0
- [high] claimed_qty_exceeds_receipt (code): Claimed 2 x 'Kopi Susu Kolonel' but the receipt shows 1.0
- [high] claim_amount_above_receipt (C4): The claim is for IDR 46,000 but the receipt total is IDR 23,000. Under C4 a claim above the receipt total is rejected, so the claim should be reduced to the receipt total or rejected.
- [high] claimed_qty_above_receipt (C9): The claim is for 2 units of Kopi Susu Kolonel but the receipt shows only 1, so the extra unit cannot be reimbursed under C9.
- [medium] price_above_list (es kopi susu): The unit price of IDR 23,000 is above the agreed maximum of IDR 20,000 for this item on the price list, so only IDR 20,000 per unit can be supported without review.

**Message:**

> Dear Member 001,
> 
> Claim VAL-001 cannot be paid as submitted, so it has been rejected.
> 
> - Amount: you claimed IDR 46,000, but the receipt total is IDR 23,000. Under C4, a claim for more than the receipt total is rejected.
> - Quantity: you claimed 2 x Kopi Susu Kolonel, but the receipt shows 1. Under C9, the quantity claimed must not exceed the receipt, so only 1 can be claimed.
> - Price: the unit price on the receipt is IDR 23,000, above the agreed maximum of IDR 20,000 on the price list. Only IDR 20,000 per unit can be supported without review.
> 
> To fix this, please resubmit the claim for one Kopi Susu Kolonel at no more than IDR 20,000. If you want the full IDR 23,000 considered, please ask for a review of the price.

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## VAL-005  (decision: needs_review)

**Verified issues (the only facts the message may use):**

- [medium] no_purpose_stated (C1): The claim states no purpose for the IDR 8,000 expense, so it must be held for review until the treasurer receives a stated club or business purpose.

**Message:**

> Dear Member 005,
> 
> Your expense claim VAL-005 for IDR 8,000 is on hold for review. The claim does not state the purpose of the expense. Under clause C1, expenses are reimbursable only when incurred for an approved club activity or business purpose, and the purpose must be stated on the claim.
> 
> To move this forward, please reply with the club or business purpose of the IDR 8,000 expense. Once I receive it, I will complete the review.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## VAL-000  (decision: approve)

**Verified issues (the only facts the message may use):**

- none

**Message:**

> Hello Member 000,
> 
> Your expense claim VAL-000 for IDR 45,500 has been approved and will be paid. The amount matches your receipt total of IDR 45,500, and no issues were found.
> 
> Thank you for submitting it.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## VAL-006  (decision: reject)

**Verified issues (the only facts the message may use):**

- [high] claim_exceeds_receipt (code): Claimed 155000 but the receipt total is 123000.0
- [high] claim_exceeds_receipt_total (C4): The claim is for IDR 155,000 but the receipt total is IDR 123,000. Under C4 a claim above the receipt total is rejected, so the claim should be reduced to at most IDR 123,000 or resubmitted with a matching receipt.

**Message:**

> Dear Member 006,
> 
> Your expense claim VAL-006 cannot be paid as submitted. You claimed IDR 155,000, but the receipt total is IDR 123,000, a difference of IDR 32,000. Under clause C4, a claim for more than the receipt total is rejected.
> 
> To proceed, you can either reduce the claim to no more than IDR 123,000, or resubmit the claim with a receipt that matches the amount you are claiming.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---

## VAL-007  (decision: needs_review)

**Verified issues (the only facts the message may use):**

- [medium] lines_vs_totals (code): Line items sum to 54091.0, but subtotal is 63636.0 and total is 59500.0
- [medium] claim_lines_vs_amount (code): Claim lines sum to 63636 but the claimed amount is 59500

**Message:**

> Subject: Claim VAL-007 is on hold
> 
> Hello Member 007,
> 
> Your claim VAL-007 for IDR 59,500 is on hold for a human decision and has not been approved yet.
> 
> Two problems were found:
> 
> - The receipt line items add up to IDR 54,091, but the receipt subtotal is IDR 63,636 and the total is IDR 59,500. These figures do not agree.
> - Your claim lines add up to IDR 63,636, but the amount you claimed is IDR 59,500.
> 
> To move this forward, please check the receipt and your claim lines, then send a corrected claim or a copy of the receipt showing the correct figures. The treasurer will review it again once we hear from you.
> 
> Kind regards,
> Club Treasurer

Accuracy: __   Evidence: __   Clarity: __   Tone: __

---
