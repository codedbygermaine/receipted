/* Numbers come from results/ in the repository (results_table.md), the same files the README reads. */
const STEPS = [["Read", "photo to line items"], ["Add up", "arithmetic in code"], ["Look up", "policy and prices"], ["Judge", "model cites a rule and a line"], ["Verify", "code drops unproven flags"], ["Decide", "approve, hold or reject"], ["Reply", "message to the member"]]
const NUMBERS = [["Planted errors caught", "48 of 50"], ["Decisions right", "83%"], ["Line items read correctly", "F1 0.92"], ["Made-up numbers", "0"], ["Cost per claim", "$0.0013"]]

export default function About() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">How it works</h1>
      <p className="mt-2 text-lg text-foreground/70">A receipt and a claim go in. The checker reads the photo, does the arithmetic in code, looks up the club's rules and prices, and flags a problem only when it can point at the receipt line and the rule.</p>
      <ol className="mt-8 divide-y border-y">
        {STEPS.map(([t, d], i) => <li key={t} className="flex gap-3 py-2.5 text-sm"><span className="w-4 tabular-nums text-foreground/60">{i + 1}</span><span className="font-medium">{t}</span><span className="text-foreground/60">{d}</span></li>)}
      </ol>
      <h2 className="mt-10 text-base font-semibold">Measured on 100 real receipts</h2>
      <dl className="mt-3 divide-y border-y">
        {NUMBERS.map(([k, v]) => <div key={k} className="flex items-baseline justify-between py-2.5 text-sm"><dt>{k}</dt><dd className="font-medium tabular-nums">{v}</dd></div>)}
      </dl>
      <p className="mt-4 text-sm text-foreground/60">Full evaluation, error analysis and code: <a className="underline underline-offset-2 hover:text-foreground" href="https://github.com/codedbygermaine/receipted" target="_blank" rel="noopener">github.com/codedbygermaine/receipted</a>. Receipts from CORD v2 (CC BY 4.0) and my own; claims and policies written for testing.</p>
    </div>
  )
}
