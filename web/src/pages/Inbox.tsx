import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { ArrowLeft, Check, Loader2, RefreshCw, X } from "lucide-react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { decide, getInbox, getJobImage, type Result } from "@/lib/api"
import { ago, claimTime, groupIssues, issueTitle, money, shortRef } from "@/lib/format"
import { IssueCard } from "@/components/IssueCard"
import { ReceiptPanel } from "@/components/ReceiptPanel"

export default function Inbox() {
  const [data, setData] = useState<{ pending: Result[]; decided: Result[] } | null>(null)
  const [error, setError] = useState(false)
  const [sel, setSel] = useState<string | null>(null)       // which claim is open
  const [mobileDetail, setMobileDetail] = useState(false)   // on small screens the detail replaces the list
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try { const d = await getInbox(); setData(d); setError(false); if (!sel || !d.pending.some(p => p.job_id === sel)) setSel(d.pending[0]?.job_id ?? null) }
    catch (e) { console.error(e); setError(true) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  const pending = data?.pending ?? []
  const summary = useMemo(() => {
    const byCur: Record<string, number> = {}
    pending.forEach(p => { const c = p.currency || "?"; byCur[c] = (byCur[c] || 0) + (p.claimed_amount || 0) })
    const oldest = pending.map(p => claimTime(p.claim_id)).filter(Boolean).sort((a, b) => a!.getTime() - b!.getTime())[0] ?? null
    const parts = [`${pending.length} waiting`]
    if (oldest) parts.push(`oldest ${ago(oldest)}`)
    const total = Object.entries(byCur).map(([c, v]) => money(v, c)).join(" + ")
    if (total) parts.push(`${total} in total`)
    return parts.join(" · ")
  }, [pending])
  const current = pending.find(p => p.job_id === sel) ?? null

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Treasurer inbox</h1>
          {data && <p className="mt-2 text-sm text-foreground/60">{pending.length ? summary : "Nothing waiting right now."}</p>}
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>{loading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />} Refresh</Button>
      </div>

      {error && <p className="mt-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">The inbox couldn't load. Try Refresh in a few seconds.</p>}

      <div className="mt-6 grid gap-5 lg:grid-cols-[300px_1fr]">
        <div className={`min-w-0 ${mobileDetail ? "hidden lg:block" : ""}`}>
          <div className="grid gap-2">
            {!data && !error && [1, 2].map(i => <div key={i} className="h-20 animate-pulse rounded-lg bg-muted" />)}
            {data && !pending.length && (
              <div className="rounded-lg border border-dashed p-6 text-center text-sm text-foreground/70">Nothing is waiting. <Link to="/claim" className="underline underline-offset-2">File a claim as a member</Link> and come back; some of the sample receipts end up here.</div>
            )}
            {pending.map(p => {
              const g = groupIssues(p.verified_issues)
              return (
                <button key={p.job_id} type="button" onClick={() => { setSel(p.job_id!); setMobileDetail(true) }} aria-pressed={sel === p.job_id}
                  className={`min-w-0 rounded-lg border p-3 text-left transition-colors ${sel === p.job_id ? "border-foreground/40 bg-muted/60" : "bg-card hover:bg-muted/40"}`}>
                  <div className="flex items-baseline justify-between gap-2"><span className="font-medium">{money(p.claimed_amount, p.currency)}</span><span className="shrink-0 text-xs text-foreground/60">{ago(claimTime(p.claim_id))}</span></div>
                  <div className="truncate text-sm text-foreground/70">{p.submitter} · {p.purpose || "no purpose given"}</div>
                  <div className="mt-1 truncate text-xs text-foreground/60">{g.length ? issueTitle(g[0].issue) + (g.length > 1 ? ` +${g.length - 1} more` : "") : "A line was hard to read"}</div>
                </button>
              )
            })}
          </div>
          {data && data.decided.length > 0 && (
            <div className="mt-6">
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-foreground/60">Recently decided</div>
              <div className="grid gap-1.5">
                {data.decided.slice(0, 8).map(p => {
                  const final = p.human?.decision ?? p.decision; const ok = final === "approve"
                  return (
                    <Link key={p.job_id} to={`/claim/${p.job_id}`} className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted">
                      <span className="truncate">{p.submitter} · {money(p.claimed_amount, p.currency)}</span>
                      <Badge variant="outline" className={`shrink-0 ${ok ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-red-200 bg-red-50 text-red-700"}`}>{ok ? "approved" : "rejected"} by {p.human ? p.human.reviewer : "the checker"}</Badge>
                    </Link>
                  )
                })}
              </div>
            </div>
          )}
        </div>
        <div className={`min-w-0 ${mobileDetail ? "" : "hidden lg:block"}`}>
          {current ? <Detail key={current.job_id} r={current} onDone={() => { setMobileDetail(false); load() }} onBack={() => setMobileDetail(false)} />
            : data && !pending.length ? null : <div className="rounded-lg border border-dashed p-10 text-center text-sm text-foreground/60">Select a claim to review it.</div>}
        </div>
      </div>
    </div>
  )
}

function Detail({ r, onDone, onBack }: { r: Result; onDone: () => void; onBack: () => void }) {
  const [img, setImg] = useState<string | null>(null)
  const [note, setNote] = useState("")
  const [who, setWho] = useState("Treasurer")
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null)
  const [done, setDone] = useState<Result | null>(null)
  const [point, setPoint] = useState<string | null>(null)
  const groups = groupIssues(r.verified_issues)
  useEffect(() => { getJobImage(r.job_id!).then(setImg).catch(() => {}) }, [r.job_id])

  async function go(decision: "approve" | "reject") {
    setBusy(decision)
    try { const res = await decide(r.job_id!, decision, note.trim(), who.trim() || "Treasurer"); setDone(res); toast.success(decision === "approve" ? "Approved. The reply to the member is ready." : "Rejected. The reply to the member is ready.") }
    catch (e) { console.error(e); toast.error("The decision couldn't be saved. Please try again in a moment.") } finally { setBusy(null) }
  }

  if (done) {
    const ok = done.decision === "approve"
    return (
      <Card><CardContent className="p-5">
        <div className={`rounded-lg border p-4 ${ok ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-red-200 bg-red-50 text-red-900"}`}>
          <div className="text-lg font-semibold">{ok ? "Approved" : "Rejected"}</div>
          <div className="text-sm">{r.submitter} will receive the reply below. <span className="opacity-70">Ref {shortRef(r.claim_id)}</span></div>
        </div>
        <div className="mt-4 rounded-lg border bg-muted/40 p-4 text-sm leading-relaxed whitespace-pre-wrap">{done.draft}</div>
        <div className="mt-4 flex gap-2"><Button variant="outline" size="sm" onClick={() => { navigator.clipboard.writeText(done.draft); toast.success("Copied") }}>Copy the reply</Button><Button size="sm" onClick={onDone}>Next claim</Button></div>
      </CardContent></Card>
    )
  }

  return (
    <Card className="overflow-hidden"><CardContent className="p-0">
      <div className="p-5">
        <Button variant="ghost" size="sm" className="-ml-2 mb-2 lg:hidden" onClick={onBack}><ArrowLeft className="size-4" /> All claims</Button>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-lg font-semibold">{r.submitter} claims {money(r.claimed_amount, r.currency)}</div>
            <div className="text-sm text-foreground/70">{r.purpose ? `For: ${r.purpose}` : "No purpose given"} · receipt total {money(r.receipt_total, r.currency)} · {ago(claimTime(r.claim_id))}</div>
          </div>
          <span className="text-xs text-foreground/60" title={r.claim_id}>Ref {shortRef(r.claim_id)}</span>
        </div>

        <h3 className="mb-2 mt-6 text-base font-semibold">Why it's here</h3>
        {groups.length ? <div className="grid gap-3">{groups.map((g, k) => <IssueCard key={k} issue={g.issue} also={g.also} onPoint={setPoint} />)}</div>
          : <p className="text-sm text-foreground/70">No rule was broken, but one line on the receipt was hard to read, so a person should check the numbers.</p>}

        <h3 className="mb-2 mt-6 text-base font-semibold">The receipt</h3>
        <ReceiptPanel src={img} items={r.items} total={r.receipt_total} currency={r.currency} readability={r.readability} highlight={point} />

        <details className="mt-6 text-sm">
          <summary className="cursor-pointer py-1 text-foreground/70">The message the member has already received</summary>
          <div className="mt-2 rounded-lg border bg-muted/40 p-4 text-sm leading-relaxed whitespace-pre-wrap">{r.draft}</div>
        </details>
      </div>

      {/* Decision bar: stays in view at the bottom while the treasurer scrolls through the evidence. */}
      <div className="sticky bottom-0 border-t bg-background/95 p-4 backdrop-blur sm:p-5">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
          <div className="grid gap-1.5">
            <Label htmlFor="note" className="block"><span>Note to the member <span className="font-normal text-foreground/60">(optional, added to the reply)</span></span></Label>
            <Input id="note" value={note} onChange={e => setNote(e.target.value)} placeholder="e.g. Purpose confirmed with the organiser" />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="signed">Signed by</Label>
            <div className="flex gap-2">
              <Input id="signed" value={who} onChange={e => setWho(e.target.value)} className="w-32" />
              <Button size="lg" className="bg-emerald-600 hover:bg-emerald-700" disabled={!!busy} onClick={() => go("approve")}>{busy === "approve" ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />} Approve</Button>
              <Button size="lg" variant="destructive" disabled={!!busy} onClick={() => go("reject")}>{busy === "reject" ? <Loader2 className="size-4 animate-spin" /> : <X className="size-4" />} Reject</Button>
            </div>
          </div>
        </div>
      </div>
    </CardContent></Card>
  )
}
