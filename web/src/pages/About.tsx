/* Numbers come from results/ in the repository (results_table.md), the same files the README reads.
   The rules are a plain-language summary of fixtures/policy_sgd.md, labelled with the clauses a verdict cites. */
const RESULTS: [string, string][] = [
  ["Approved", "Receipted approves the claim automatically. No manual approval is needed."],
  ["Needs review", "The claim waits for a person to check it and approve or reject it."],
  ["Rejected", "Receipted rejects the claim automatically and explains the problem."],
]
const RULES: [string, string][] = [
  ["C1", "The claim must say what the money was for."],
  ["C4", "The amount claimed can't be more than the receipt total."],
  ["C3", "No alcohol or tobacco."],
  ["C6", "No personal items. Medicines and first-aid supplies are held until the business purpose is confirmed."],
  ["C12", "Meals over SGD 40 a person are held for an approver."],
  ["C7", "Claims over SGD 500 need two approvers."],
  ["C9", "A receipt can't be claimed twice."],
]
const NUMBERS = [["Planted errors caught", "48 of 50"], ["Clean claims wrongly flagged", "8 of 41"], ["Decision accuracy", "83%"], ["Receipt totals read correctly", "97%"], ["Fabricated digits when the total was hidden", "0 of 98"], ["Model cost per claim (USD)", "$0.0013"]]

export default function About() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">How it works</h1>

      <h2 className="mt-8 text-base font-semibold">From receipt to decision</h2>
      <ol className="mt-3 grid gap-2">
        {["Upload a receipt, enter the amount you’re claiming and say what it was for.",
          "Receipted reads the receipt, checks the amounts and checks whether the expense policy allows the purchase.",
          "It gives the claim one of three results."].map((t, i) => (
          <li key={i} className="flex gap-3 text-sm"><span className="grid size-6 shrink-0 place-items-center rounded-full bg-foreground text-xs text-background">{i + 1}</span><span className="pt-0.5">{t}</span></li>
        ))}
      </ol>
      <dl className="mt-4 divide-y border-y">
        {RESULTS.map(([k, v]) => <div key={k} className="grid gap-1 py-2.5 text-sm sm:grid-cols-[8rem_1fr]"><dt className="font-medium">{k}</dt><dd className="text-foreground/70">{v}</dd></div>)}
      </dl>
      <p className="mt-3 text-sm text-foreground/60">Approval here is a decision. It doesn’t transfer money.</p>

      <h2 className="mt-10 text-base font-semibold">Reviewing a claim</h2>
      <p className="mt-2 text-sm text-foreground/70">Claims marked “Needs review” appear in the approvals inbox. The approver sees the receipt, the flagged items and the reasons for flagging them, then approves or rejects the claim, or asks the claimant a question.</p>

      <h2 className="mt-10 text-base font-semibold">Rules used in this demo</h2>
      <ul className="mt-3 grid gap-1.5 text-sm text-foreground/80">{RULES.map(([id, r]) => <li key={id} className="flex gap-3"><span className="w-8 shrink-0 tabular-nums text-foreground/60">{id}</span><span>{r}</span></li>)}</ul>
      <p className="mt-2 text-xs text-foreground/60">The numbers are the clauses a verdict cites. The full policy is in the repository.</p>

      <h2 className="mt-10 text-base font-semibold">Test results</h2>
      <p className="mt-1 text-sm text-foreground/60">Tested on 100 real receipts with 100 claims, 50 of them with a deliberate mistake.</p>
      <dl className="mt-3 divide-y border-y">
        {NUMBERS.map(([k, v]) => <div key={k} className="flex items-baseline justify-between py-2.5 text-sm"><dt>{k}</dt><dd className="font-medium tabular-nums">{v}</dd></div>)}
      </dl>
      <p className="mt-4 text-sm text-foreground/60">Full evaluation, limitations and code: <a className="underline underline-offset-2 hover:text-foreground" href="https://github.com/codedbygermaine/receipted/blob/main/docs/evaluation.md" target="_blank" rel="noopener">docs/evaluation.md</a></p>
    </div>
  )
}
