import { useEffect, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { ArrowLeft, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ask, decide, getInbox, getJobImage, hasAnswer, waitingForClaimant, type Result } from "@/lib/api"
import { ago, claimTime, groupIssues, issueTitle, money } from "@/lib/format"
import { ClaimReview } from "@/components/ClaimReview"

/* The approver's queue. One list, one claim at a time, the decision last. */
export default function Inbox() {
  const [data, setData] = useState<{ pending: Result[]; decided: Result[] } | null>(null)
  const [error, setError] = useState(false)
  const [sel, setSel] = useState<string | null>(null)
  const [mobileOpen, setMobileOpen] = useState(false)   // on small screens the claim replaces the list
  const [params] = useSearchParams()
  const wanted = params.get("job")   // "Review this claim" on a verdict opens that claim here

  async function load(keep?: string | null) {
    try {
      const d = await getInbox(); setData(d); setError(false)
      const want = keep ?? sel
      setSel(want && d.pending.some(p => p.job_id === want) ? want : d.pending[0]?.job_id ?? null)
    } catch (e) { console.error(e); setError(true) }
  }
  useEffect(() => { load(wanted); if (wanted) setMobileOpen(true); const onFocus = () => load(); window.addEventListener("focus", onFocus); return () => window.removeEventListener("focus", onFocus) }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  const pending = data?.pending ?? []
  const current = pending.find(p => p.job_id === sel) ?? null

  /** After a decision the row leaves the queue and the next claim opens, so the approver never hunts. */
  function settled(jobId: string, res: Result) {
    const i = pending.findIndex(p => p.job_id === jobId)
    const next = pending[i + 1] ?? pending[i - 1] ?? null
    setData(d => d && { pending: d.pending.filter(p => p.job_id !== jobId), decided: [{ ...res, job_id: jobId }, ...d.decided] })
    setSel(next?.job_id ?? null)
    if (!next) setMobileOpen(false)
  }

  return (
    <div>
      <div className={`${mobileOpen ? "hidden lg:flex" : "flex"} items-baseline justify-between`}>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Approvals{data ? ` (${pending.length})` : ""}</h1>
      </div>
      {error && <p className="mt-4 text-sm text-foreground/70">The inbox couldn't load. Try Refresh in a moment.</p>}

      <div className="mt-6 grid gap-8 lg:grid-cols-[320px_1fr]">
        <div className={mobileOpen ? "hidden lg:block" : ""}>
          {!data && !error && <div className="divide-y border-y">{[0, 1, 2].map(i => <div key={i} className="py-3"><div className="h-4 w-24 animate-pulse rounded bg-muted" /><div className="mt-2 h-3 w-40 animate-pulse rounded bg-muted" /></div>)}</div>}
          {data && pending.length === 0 && <p className="text-sm text-foreground/60">Nothing waiting.</p>}
          {pending.length > 0 && (
            <div className="divide-y border-y">
              {pending.map(p => {
                const g = groupIssues(p.verified_issues); const on = sel === p.job_id
                return (
                  <button key={p.job_id} type="button" onClick={() => { setSel(p.job_id!); setMobileOpen(true) }} aria-current={on || undefined}
                    className={`block w-full border-l-2 px-3 py-3 text-left transition-colors ${on ? "border-foreground bg-muted" : "border-transparent hover:bg-muted/50"}`}>
                    <div className="flex items-baseline justify-between gap-3"><span className="font-medium tabular-nums">{money(p.claimed_amount, p.currency)}</span><span className="shrink-0 text-xs text-foreground/60">{ago(claimTime(p.claim_id))}</span></div>
                    <div className="mt-0.5 truncate text-sm text-foreground/70">{p.submitter}{p.purpose ? `, ${p.purpose}` : ""}</div>
                    <div className="mt-0.5 truncate text-sm text-foreground/60">{waitingForClaimant(p) ? "Waiting for the claimant" : hasAnswer(p) ? "Answered" : g.length ? g.slice(0, 2).map(x => issueTitle(x.issue)).join(", ") + (g.length > 2 ? ` and ${g.length - 2} more` : "") : "A line was hard to read"}</div>
                  </button>
                )
              })}
            </div>
          )}
          {data && data.decided.length > 0 && (
            <details className="mt-6 text-sm">
              <summary className="cursor-pointer py-1 text-foreground/60 hover:text-foreground">Decided recently</summary>
              <ul className="mt-1 divide-y border-y">
                {data.decided.slice(0, 10).map(p => {
                  const final = p.human?.decision ?? p.decision
                  return (
                    <li key={p.job_id}><Link to={`/claim/${p.job_id}`} className="flex items-baseline justify-between gap-3 px-3 py-2 hover:bg-muted/50">
                      <span className="truncate text-foreground/80">{p.submitter}, {money(p.claimed_amount, p.currency)}</span>
                      <span className="shrink-0 text-xs text-foreground/60">{final === "approve" ? "approved" : "rejected"}{p.human ? ` by ${p.human.reviewer}` : ""}</span>
                    </Link></li>
                  )
                })}
              </ul>
            </details>
          )}
        </div>

        <div className={`min-w-0 ${mobileOpen ? "" : "hidden lg:block"}`}>
          {current ? <Claim key={current.job_id} r={current} onBack={() => setMobileOpen(false)} onSettled={settled} />
            : !data ? <p className="pt-2 text-sm text-foreground/60">Loading claims…</p> : null}
        </div>
      </div>
    </div>
  )
}

function Claim({ r: initial, onBack, onSettled }: { r: Result; onBack: () => void; onSettled: (jobId: string, res: Result) => void }) {
  const nav = useNavigate()
  const [r, setR] = useState(initial)
  const [img, setImg] = useState<string | null>(null)
  const [asking, setAsking] = useState(false)
  const [question, setQuestion] = useState("")
  const [sending, setSending] = useState(false)
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null)
  const [confirmReject, setConfirmReject] = useState(false)
  useEffect(() => { getJobImage(r.job_id!).then(setImg).catch(() => {}) }, [r.job_id])

  async function sendQuestion() {
    if (!question.trim()) return
    setSending(true)
    try { const res = await ask(r.job_id!, question.trim(), "Finance"); setR(res); setAsking(false); setQuestion(""); toast(`Sent. ${r.submitter} can answer from their claim page.`) }
    catch (e) { console.error(e); toast("The question didn't send. Try again in a moment.") } finally { setSending(false) }
  }

  async function go(decision: "approve" | "reject") {
    setBusy(decision)
    try {
      const res = await decide(r.job_id!, decision, note.trim(), "Finance")
      toast(decision === "approve" ? `Approved. ${r.submitter} gets the reply.` : `Rejected. ${r.submitter} gets the reply.`, { action: { label: "Read it", onClick: () => nav(`/claim/${r.job_id}`) } })
      onSettled(r.job_id!, res)
    } catch (e) { console.error(e); toast.error("That didn't save. Try again in a moment."); setBusy(null) }
  }

  return (
    <article>
      <button type="button" onClick={onBack} className="-ml-1 mb-3 inline-flex items-center gap-1 text-sm text-foreground/60 hover:text-foreground lg:hidden"><ArrowLeft className="size-4" /> Approvals</button>
      <h2 className="text-lg font-semibold">{r.submitter} claims {money(r.claimed_amount, r.currency)}</h2>
      <p className="mt-0.5 text-sm text-foreground/60">{r.purpose ? `${r.purpose}, ` : "No purpose given, "}{ago(claimTime(r.claim_id))}</p>

      <div className="mt-6"><ClaimReview r={r} image={img} /></div>

      {r.thread && r.thread.length > 0 && (
        <div className="mt-6 divide-y border-y text-sm">
          {r.thread.map((m, i) => <div key={i} className="py-2.5"><span className="text-foreground/60">{m.role === "approver" ? "Finance asked" : `${m.name} answered`}, {ago(new Date(m.at))}</span><div className="mt-0.5">{m.text}</div></div>)}
        </div>
      )}

      <details className="mt-6 text-sm">
        <summary className="cursor-pointer py-1 text-foreground/60 hover:text-foreground">The message {r.submitter} has received</summary>
        <div className="mt-2 whitespace-pre-wrap rounded-md bg-muted/50 p-4 leading-relaxed text-foreground/80">{r.draft}</div>
      </details>

      <div className="mt-8 border-t pt-6">
        <Input value={note} onChange={e => setNote(e.target.value)} placeholder="Add a note for the reply" aria-label="Note for the reply" />
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          {asking ? (
            <span className="flex flex-1 items-center gap-2"><Input autoFocus value={question} onChange={e => setQuestion(e.target.value)} placeholder="What do you need to know?" aria-label="Question for the claimant" onKeyDown={e => e.key === "Enter" && sendQuestion()} />
              <Button size="lg" disabled={sending || !question.trim()} onClick={sendQuestion}>{sending ? <Loader2 className="size-4 animate-spin motion-reduce:animate-none" /> : null} Send</Button>
              <Button size="lg" variant="ghost" onClick={() => setAsking(false)}>Cancel</Button></span>
          ) : <>
          <Button size="lg" disabled={!!busy} onClick={() => go("approve")}>{busy === "approve" ? <Loader2 className="size-4 animate-spin motion-reduce:animate-none" /> : null} Approve {money(r.claimed_amount, r.currency)}</Button>
          {confirmReject
            ? <span className="inline-flex items-center gap-2 text-sm"><span>Reject {r.submitter}'s claim?</span><Button size="sm" variant="destructive" disabled={!!busy} onClick={() => go("reject")}>{busy === "reject" ? <Loader2 className="size-4 animate-spin motion-reduce:animate-none" /> : null} Reject</Button><Button size="sm" variant="ghost" onClick={() => setConfirmReject(false)}>Cancel</Button></span>
            : <Button size="lg" variant="ghost" disabled={!!busy} onClick={() => setConfirmReject(true)}>Reject</Button>}
          {!waitingForClaimant(r) && <Button size="lg" variant="ghost" disabled={!!busy} onClick={() => setAsking(true)}>Ask the claimant</Button>}
          </>}
        </div>
      </div>
    </article>
  )
}
