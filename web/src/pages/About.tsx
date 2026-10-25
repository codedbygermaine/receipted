/* Numbers come from results/ in the repository (results_table.md), the same files the README reads.
   The rules are a plain-language summary of fixtures/policy_sgd.md. */
const STEPS = [
  ["Reads the receipt", "The photo becomes a list of items and prices."],
  ["Does the maths", "Do the items add up to the total? Does the claim match the receipt?"],
  ["Looks up the rules", "The demo policy and its reference prices."],
  ["Checks the claim", "Is anything on the receipt or in the claim against a rule? Every flag has to name the line and the rule."],
  ["Double-checks", "Every flag's evidence and arithmetic are checked in code; unsupported flags are dropped."],
  ["Decides", "Approve, hold for an approver, or reject."],
  ["Writes the reply", "A short message to the claimant saying what happens next."],
]
const RULES = [
  "The claim must say what the money was for.",
  "The amount claimed can't be more than the receipt total.",
  "No alcohol or tobacco.",
  "No personal items. Medicines and first-aid supplies are held until the business purpose is confirmed.",
  "Meals over $40 a person are held for an approver.",
  "Claims over $500 need two approvers.",
  "A receipt can't be claimed twice.",
]
const NUMBERS = [["Planted errors caught", "48 of 50"], ["Clean claims wrongly flagged", "8 of 41"], ["Decision accuracy", "83%"], ["Receipt totals read correctly", "97%"], ["Fabricated digits when the total was hidden", "0 of 98"], ["Model cost per claim (USD)", "$0.0013"]]

export default function About() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">How it works</h1>

      <h2 className="mt-10 text-base font-semibold">What happens when you press Check</h2>
      <ol className="mt-4 grid gap-3">
        {STEPS.map(([t, d], i) => (
          <li key={t} className="flex gap-3"><span className="grid size-6 shrink-0 place-items-center rounded-full bg-foreground text-xs text-background">{i + 1}</span><div><div className="text-sm font-medium">{t}</div><div className="text-sm text-foreground/70">{d}</div></div></li>
        ))}
      </ol>

      <h2 className="mt-10 text-base font-semibold">Demo expense policy (SGD)</h2>
      <ul className="mt-3 grid gap-1.5 text-sm text-foreground/80">{RULES.map(r => <li key={r}>{r}</li>)}</ul>

      <h2 className="mt-10 text-base font-semibold">How well it does</h2>
      <p className="mt-1 text-sm text-foreground/60">Tested on 100 real receipts with 100 claims, 50 of them with a deliberate mistake.</p>
      <dl className="mt-3 divide-y border-y">
        {NUMBERS.map(([k, v]) => <div key={k} className="flex items-baseline justify-between py-2.5 text-sm"><dt>{k}</dt><dd className="font-medium tabular-nums">{v}</dd></div>)}
      </dl>
      <p className="mt-4 text-sm text-foreground/60">Full evaluation: <a className="underline underline-offset-2 hover:text-foreground" href="https://github.com/codedbygermaine/receipted/blob/main/docs/evaluation.md" target="_blank" rel="noopener">docs/evaluation.md</a></p>
    </div>
  )
}
