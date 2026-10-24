import { Card, CardContent } from "@/components/ui/card"

/* Every number here comes from results/ in the repository (results_table.md, metrics.json), the same files the
   README reads. If the evaluation is re-run, update both. */
const STEPS = [
  ["Read", "A vision model turns the photo into line items and totals, with a confidence per line."],
  ["Add up", "Plain Python checks the arithmetic: lines against totals, claim against receipt. Code is exact; models are not."],
  ["Look up", "The club's policy clauses and agreed price list are retrieved for this receipt's currency."],
  ["Judge", "A model asks whether a specific line breaks a specific rule, and must cite both."],
  ["Verify", "Code throws away any complaint whose clause or receipt line doesn't exist, or whose numbers don't hold."],
  ["Decide", "Approve, hold for a person, or reject. Unreadable receipts always go to a person."],
  ["Reply", "A message to the member, written from the verified issues only."],
]

export default function About() {
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">How it works, and how well</h1>
      <p className="mt-2 text-lg text-foreground/70">Receipted checks an expense claim the way a careful treasurer would, and refuses to flag anything it can't point at.</p>

      <h2 className="mb-3 mt-10 text-sm font-medium uppercase tracking-wide text-foreground/70">Seven steps</h2>
      <ol className="grid gap-2 sm:grid-cols-2">
        {STEPS.map(([t, d], i) => (
          <li key={t} className="flex gap-3 rounded-lg border bg-card p-3"><span className="grid size-6 shrink-0 place-items-center rounded-full bg-foreground text-xs text-background">{i + 1}</span><div><div className="text-sm font-medium">{t}</div><div className="text-sm text-foreground/70">{d}</div></div></li>
        ))}
      </ol>

      <h2 className="mb-3 mt-10 text-sm font-medium uppercase tracking-wide text-foreground/70">Measured, on real receipts</h2>
      <Card><CardContent className="p-0 divide-y">
        <Row k="Planted errors caught" v="48 of 50" n="100 test claims on 100 real receipts, five error types; 95% CI 90–100%" />
        <Row k="Decision accuracy" v="83%" n="approve / hold / reject against the intended answer; 8 of 41 clean claims got a flag" />
        <Row k="Line items read correctly" v="F1 0.92" n="small and large model alike; printed totals right 97% of the time" />
        <Row k="Made-up numbers" v="0" n="with the printed total hidden on 98 receipts, 84% said 'not printed' and none invented digits" />
        <Row k="Reply quality" v="4.6 – 5.0 / 5" n="accuracy, evidence, clarity, tone judged by a larger model; a person agreed within one point on 39 of 40 scores" />
        <Row k="Cost and time" v="$0.0013 · 5 s" n="per claim with the small model; the large model matched it at 30× the cost, so the small one ships" />
      </CardContent></Card>
      <p className="mt-3 text-sm text-foreground/70">Numbers come from the evaluation scripts in the repository and are reproduced in its README; intervals are bootstrap 95% CIs. Prompts were tuned on a separate validation split and frozen before the test split was touched.</p>

      <h2 className="mb-3 mt-10 text-sm font-medium uppercase tracking-wide text-foreground/70">Built like a production system</h2>
      <ul className="grid gap-2 text-sm sm:grid-cols-2">
        {["Every flag must cite a receipt line and a policy clause, and a verifier in plain code drops the ones that don't hold.",
          "Large claims get three independent model judgements and keep the majority.",
          "Confidence is calibrated on real documents: lines marked 'low' were wrong three times in four, so they go to a person.",
          "Human decisions are kept as labelled cases, and one in ten approvals is sampled for audit.",
          "Card numbers are masked in code before anything is stored. A policy per currency, so a Singapore receipt meets Singapore rules.",
          "Tests and a regression gate run on every push; the API runs serverless in Singapore."].map(t => <li key={t} className="rounded-lg border bg-card p-3 text-foreground/70">{t}</li>)}
      </ul>

      <h2 className="mb-3 mt-10 text-sm font-medium uppercase tracking-wide text-foreground/70">Honest limits</h2>
      <div className="space-y-2 text-sm text-foreground/70">
        <p>The claims, price lists and policies were written for testing; the receipts are real. Receipts come from the CORD v2 dataset (Indonesian, CC BY 4.0), from the author's own purchases in Singapore, and from ten openly licensed receipts from the UK, US and Australia.</p>
        <p>Dates are not checked. Hand-written receipts and very blurry photos go straight to a person. This public demo shares one small daily budget, and anything uploaded can be seen in the treasurer inbox for seven days.</p>
        <p>Found a flaw? The code, the evaluation, the error analysis and a learning log are all public: <a className="underline underline-offset-2" href="https://github.com/codedbygermaine/receipted" target="_blank" rel="noopener">github.com/codedbygermaine/receipted</a>.</p>
      </div>
    </div>
  )
}

function Row({ k, v, n }: { k: string; v: string; n: string }) {
  return (
    <div className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-[11rem_7rem_1fr] sm:items-baseline sm:gap-3">
      <div className="font-medium">{k}</div>
      <div className="text-lg font-semibold tabular-nums">{v}</div>
      <div className="text-foreground/70">{n}</div>
    </div>
  )
}
