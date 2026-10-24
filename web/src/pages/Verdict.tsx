import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ArrowLeft, Check, Clock, X } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { getJob, getJobImage, type Result } from "@/lib/api"
import { DECISION, groupIssues, money, shortRef } from "@/lib/format"
import { IssueCard } from "@/components/IssueCard"
import { ReceiptPanel } from "@/components/ReceiptPanel"

/* The claim page hands its result over in memory so the verdict shows instantly; a direct visit to the link
   fetches the job (and its image) from the API instead. */
let handoff: { result: Result; image: string } | null = null
export function rememberResult(result: Result, image: string) { handoff = { result, image } }

const TONE = { ok: { bg: "bg-emerald-50 border-emerald-200 text-emerald-900", icon: Check }, hold: { bg: "bg-amber-50 border-amber-200 text-amber-900", icon: Clock }, no: { bg: "bg-red-50 border-red-200 text-red-900", icon: X } }

export default function Verdict() {
  const { jobId } = useParams()
  const [r, setR] = useState<Result | null>(handoff?.result ?? null)
  const [img, setImg] = useState<string | null>(handoff?.image ?? null)
  const [point, setPoint] = useState<string | null>(null)
  const [missing, setMissing] = useState(false)

  useEffect(() => {
    if (handoff && (handoff.result.job_id === jobId || jobId === "latest")) { handoff = null; return }
    if (!jobId || jobId === "latest") { setMissing(true); return }
    getJob(jobId).then(res => { if (res) setR(res); else setMissing(true) }).catch(() => setMissing(true))
    getJobImage(jobId).then(setImg).catch(() => {})
  }, [jobId])

  if (missing) return <Empty />
  if (!r) return <div className="mx-auto max-w-3xl animate-pulse space-y-4"><div className="h-24 rounded-lg bg-muted" /><div className="h-64 rounded-lg bg-muted" /></div>

  const final = r.human?.decision ?? r.decision
  const d = DECISION[final]
  const T = TONE[d.tone]; const Icon = T.icon
  const held = final === "needs_review"
  const groups = groupIssues(r.verified_issues)
  const copy = () => { navigator.clipboard.writeText(r.draft); toast.success("Copied") }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <Button asChild variant="ghost" size="sm"><Link to="/claim"><ArrowLeft className="size-4" /> Check another</Link></Button>
        <span className="text-xs text-foreground/60" title={r.claim_id}>Ref {shortRef(r.claim_id)}</span>
      </div>

      <div className={`rounded-xl border p-5 sm:p-6 ${T.bg}`}>
        <div className="flex items-start gap-4">
          <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full bg-white/70"><Icon className="size-5" /></span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{d.label}</h1>
            {r.human && <p className="mt-1 text-[15px]">Decided by {r.human.reviewer}{r.human.note ? `: ${r.human.note}` : ""}</p>}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <span>Claimed <b>{money(r.claimed_amount, r.currency)}</b></span>
          <span>Receipt total <b>{money(r.receipt_total, r.currency)}</b></span>
          {r.purpose && <span className="opacity-80">For: {r.purpose}</span>}
        </div>
      </div>

      {groups.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-base font-semibold">{r.human ? "What the treasurer looked at" : groups.length === 1 ? "What was found" : `What was found (${groups.length})`}</h2>
          <div className="grid gap-3">{groups.map((g, k) => <IssueCard key={k} issue={g.issue} also={g.also} resolved={!!r.human} onPoint={setPoint} />)}</div>
          <p className="mt-2 text-xs text-foreground/60">Hover or tap a card to see the receipt line it points at.</p>
        </section>
      )}

      <section className="mt-8">
        <h2 className="mb-3 text-base font-semibold">What the receipt says</h2>
        <Card><CardContent className="p-4"><ReceiptPanel src={img} items={r.items} total={r.receipt_total} currency={r.currency} readability={r.readability} highlight={point} /></CardContent></Card>
      </section>

      <details className="mt-8 group">
        <summary className="cursor-pointer list-none text-sm font-medium text-foreground/70 hover:text-foreground">
          <span className="group-open:hidden">{held ? "Read the message you've been sent" : "Read the full message"}</span><span className="hidden group-open:inline">Hide the message</span>
        </summary>
        <div className="relative mt-3 rounded-xl border bg-card p-5 text-[15px] leading-relaxed whitespace-pre-wrap">{r.draft}
          <Button variant="outline" size="sm" className="absolute right-3 top-3" onClick={copy}>Copy</Button>
        </div>
      </details>
      {held && <p className="mt-6 text-sm text-foreground/70">Playing the treasurer too? <Link to="/inbox" className="underline underline-offset-2">Open the inbox</Link>, this claim is waiting there.</p>}
    </div>
  )
}

function Empty() {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <h1 className="text-xl font-semibold">That claim isn't here any more</h1>
      <p className="mt-2 text-sm text-foreground/70">Demo results are kept for seven days. Start a new check instead.</p>
      <Button asChild className="mt-6"><Link to="/claim">Claim an expense</Link></Button>
    </div>
  )
}
