import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { answer, getJob, getJobImage, waitingForClaimant, type Result } from "@/lib/api"
import { DECISION, money } from "@/lib/format"
import { ClaimReview } from "@/components/ClaimReview"

/* The claim page hands its result over in memory so the verdict shows instantly; a direct visit to the link
   fetches the job (and its image) from the API instead. */
let handoff: { result: Result; image: string } | null = null
export function rememberResult(result: Result, image: string) { handoff = { result, image } }



const WORD = { ok: "text-emerald-700", hold: "text-amber-700", no: "text-red-700" }

export default function Verdict() {
  const { jobId } = useParams()
  const [r, setR] = useState<Result | null>(handoff?.result ?? null)
  const [img, setImg] = useState<string | null>(handoff?.image ?? null)
  const [missing, setMissing] = useState(false)
  const [reply, setReply] = useState("")
  const [sending, setSending] = useState(false)

  useEffect(() => {
    if (handoff && (handoff.result.job_id === jobId || jobId === "latest")) { handoff = null; return }
    if (!jobId || jobId === "latest") { setMissing(true); return }
    getJob(jobId).then(res => { if (res) setR(res); else setMissing(true) }).catch(() => setMissing(true))
    getJobImage(jobId).then(setImg).catch(() => {})
  }, [jobId])

  async function send() {
    if (!r || !reply.trim()) return
    setSending(true)
    try { setR(await answer(r.job_id!, reply.trim())); setReply(""); toast("Sent to the approver.") }
    catch (e) { console.error(e); toast("That didn't send. Try again in a moment.") } finally { setSending(false) }
  }

  if (missing) return <Empty />
  if (!r) return <div className="mx-auto max-w-3xl animate-pulse space-y-4"><div className="h-10 w-64 rounded bg-muted" /><div className="h-64 rounded bg-muted" /></div>

  const final = r.human?.decision ?? r.decision
  const d = DECISION[final]
  const held = final === "needs_review"

  return (
    <div className="enter mx-auto max-w-3xl">
      <Link to="/claim" className="mb-6 inline-flex items-center gap-1 py-1 text-sm text-foreground/60 hover:text-foreground"><ArrowLeft className="size-4" /> Check another</Link>

      <h1 className={`text-3xl font-semibold tracking-tight ${WORD[d.tone]}`}>{waitingForClaimant(r) ? "A question for you" : d.label}</h1>
      <p className="mt-2 max-w-xl text-foreground/70">
        {r.human ? <>Decided by {r.human.reviewer}{r.human.note ? `: ${r.human.note.replace(/[.\s]+$/, "")}` : ""}. </> : null}
        Claimed {money(r.claimed_amount, r.currency)}{r.purpose ? ` for ${r.purpose}` : ""}.
      </p>

      {r.emailed && !r.human && <p className="mt-2 text-sm text-foreground/60">Questions and the decision will be emailed to you.</p>}
      {r.thread && r.thread.length > 0 && (
        <div className="mt-6 divide-y border-y text-sm">
          {r.thread.map((m, i) => <div key={i} className="py-2.5"><span className="text-foreground/60">{m.role === "approver" ? `${m.name} asks` : "You answered"}</span><div className="mt-0.5">{m.text}</div></div>)}
        </div>
      )}
      {waitingForClaimant(r) && !r.human && (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Input value={reply} onChange={e => setReply(e.target.value)} placeholder="Your answer" aria-label="Your answer" className="flex-1" onKeyDown={e => e.key === "Enter" && send()} />
          <Button disabled={sending || !reply.trim()} onClick={send}>Send answer</Button>
        </div>
      )}

      <div className="mt-8"><ClaimReview r={r} image={img} muted={!!r.human} /></div>

      <details className="mt-8 text-sm">
        <summary className="cursor-pointer py-1 text-foreground/60 hover:text-foreground">Claim message</summary>
        <div className="relative mt-2 whitespace-pre-wrap rounded-md bg-muted/50 p-4 pr-20 leading-relaxed text-foreground/80">{r.draft}
          <Button variant="ghost" size="sm" className="absolute right-2 top-2" onClick={() => { navigator.clipboard.writeText(r.draft); toast("Copied") }}>Copy</Button>
        </div>
      </details>
      {held && <p className="mt-6 text-sm"><Link to={`/inbox?job=${r.job_id ?? ""}`} className="text-foreground/70 underline underline-offset-2 hover:text-foreground">Review this claim as the approver</Link></p>}
    </div>
  )
}

function Empty() {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <h1 className="text-xl font-semibold">That claim isn't here any more</h1>
      <p className="mt-2 text-sm text-foreground/70">Demo results are kept for seven days.</p>
      <Button asChild className="mt-6"><Link to="/claim">Claim an expense</Link></Button>
    </div>
  )
}
