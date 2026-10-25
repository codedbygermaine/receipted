# Receipted: a one-page case study

**What it is.** An agent that checks an expense claim against a receipt photo, a price list and a written policy, and only flags a problem when it can point at the receipt line and the rule. Live at https://codedbygermaine.github.io/receipted/ ; code at https://github.com/codedbygermaine/receipted.

**Who it is for.** Two people with different questions. The person claiming asks "will I get my money, and if not, why not?" The approver asks "what do I actually need to look at?" I built it for my club's treasurer and designed it for any team that reimburses expenses. Finance teams do this check by hand today: does the claim match the receipt, do the numbers add up, is the price what we agreed, does anything break a rule. It is slow, and errors slip through. Off-the-shelf tools read invoices well; the team's own price list and policy are where the checking goes wrong.

**How it works, in one breath.** A vision model reads the photo into line items and totals, each with a confidence. Plain Python does every piece of arithmetic, because code is exact and models are not. The club's policy clauses and agreed prices are retrieved for the receipt's currency. A model is asked whether a specific line breaks a specific rule and must cite both. A verifier in plain code throws away any complaint whose clause or receipt line doesn't exist, or whose numbers don't hold when redone. Then a decision: approve, hold for a person, or reject. Unreadable receipts always go to a person. Finally a reply to the claimant, written only from the verified issues.

**What was measured, and how honestly.** 100 real receipts (CORD v2, CC BY 4.0) with 100 test claims I wrote, each with a known planted error or none. Prompts were tuned on a separate validation split and frozen. The test split was run twice, before and after three fixes from the first error analysis, and both runs are reported so the second isn't mistaken for a first. Every number below is written by a script into `results/`.

| Measure | Result |
|---|---|
| Planted errors caught | 48 of 50 (95% CI 87–99%) |
| Decision accuracy | 83% |
| Clean claims wrongly flagged | 8 of 41, an upper bound: at least 3 are real breaches my labels missed |
| Line items read correctly | F1 0.92, same for the small and the large model |
| Made-up numbers when the total is hidden | 0 in 98 receipts; 84% said "not printed" |
| Reply quality | Scored 4.6 to 5.0 out of 5 on four criteria by a model judge; a human check of ten drafts agreed within one point on 39 of 40 scores, a small check rather than a validation |
| Cost and time per claim | $0.0013 of model cost and about 5 s of model time with the small model, about 9 s end to end on the live demo once the server is warm. The large model caught no more planted errors on the claim-checking task at 30× the cost, though it read the Singapore receipts more precisely (F1 0.95 against 0.79) |

**Three things that went wrong, and what they taught.**

1. *A correct feature broke the demo.* The duplicate-receipt detector rejected the second visitor who clicked the same sample receipt, exactly as the policy says it should. A model being right and a product being right are different things; sample runs now bypass the registry, and an independent review found eleven more problems of the same family.
2. *The first live checks took 54 seconds.* Guessing was useless, so the API started returning a per-step timing trace. Retrieval was 27 s of it: one embedding pass per query, 17 queries per claim, plus a 20-second model load on a CPU the runtime couldn't identify. Batched queries, a warm-up call fired while the member fills the form, and more memory brought a warm check to 9 s.
3. *The first two interfaces were organised around the pipeline.* Tabs for queue and audit log, metric chips on the first screen, a seven-stage progress bar, words like "verifier" and "severity". An independent design review followed, and the product now has one screen per question a person actually has.

**What I would do with another month.** Check dates and deadlines (the dataset has none). Add a per-line discount field so percentage discounts stop tripping the arithmetic check. Route receipts the small model finds unclear to the large one, and measure whether it pays. Replay the treasurer's corrections, which are already stored as labelled cases, as the next evaluation set.

**Why it matters for the roles I'm applying to.** The hard part wasn't calling a model. It was deciding what the model is allowed to say (only what it can cite), what code must do instead (all arithmetic), when a person must be in the loop (unreadable or borderline), how to measure it without fooling myself (frozen prompts, two runs disclosed, intervals on everything), and what each of two users needs to see. It is all in the repo: README, evaluation, error analysis, and a learning log of every phase.

**What was mine, and what the tools did.** Claude Code wrote most of the code. The decisions above were mine: the workflow and where code must do the work instead of the model, the test claims and their planted errors, the evaluation criteria and the two-run disclosure, the human-in-the-loop boundary, and every product change made after a failure. I verified the work by reading the code for each phase, running the evaluation scripts myself, hand-scoring a sample of the replies against the model judge, and keeping a learning log I can defend in an interview without the tools.
