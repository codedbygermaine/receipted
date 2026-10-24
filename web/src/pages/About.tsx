import { Card, CardContent } from "@/components/ui/card"

/* Numbers come from results/ in the repository (results_table.md), the same files the README reads. */
const STEPS = [["Read", "photo → line items"], ["Add up", "arithmetic in code"], ["Look up", "policy and prices"], ["Judge", "model cites a rule and a line"], ["Verify", "code drops unproven flags"], ["Decide", "approve · hold · reject"], ["Reply", "message to the member"]]

export default function About() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">How it works</h1>
      <p className="mt-2 text-lg text-foreground/70">A receipt and a claim go in. The checker reads the photo, does the arithmetic in code, looks up the club's rules and prices, and flags a problem only when it can point at the receipt line and the rule.</p>

      <ol className="mt-8 grid gap-2 sm:grid-cols-2">
        {STEPS.map(([t, d], i) => (
          <li key={t} className="flex items-center gap-3 rounded-lg border bg-card px-3 py-2.5 text-sm"><span className="grid size-6 shrink-0 place-items-center rounded-full bg-foreground text-xs text-background">{i + 1}</span><span className="font-medium">{t}</span><span className="text-foreground/60">{d}</span></li>
        ))}
      </ol>

      <h2 className="mt-10 text-base font-semibold">Measured on 100 real receipts</h2>
      <Card className="mt-3"><CardContent className="divide-y p-0">
        <Row k="Planted errors caught" v="48 of 50" />
        <Row k="Decisions right" v="83%" />
        <Row k="Line items read correctly" v="F1 0.92" />
        <Row k="Made-up numbers" v="0" />
        <Row k="Cost per claim" v="$0.0013" />
      </CardContent></Card>
      <p className="mt-3 text-sm text-foreground/60">Full evaluation, error analysis and code: <a className="underline underline-offset-2" href="https://github.com/codedbygermaine/receipted" target="_blank" rel="noopener">github.com/codedbygermaine/receipted</a>. Receipts from CORD v2 (CC BY 4.0) and my own; claims and policies written for testing.</p>
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex items-baseline justify-between px-4 py-3 text-sm"><span>{k}</span><span className="text-lg font-semibold tabular-nums">{v}</span></div>
}
