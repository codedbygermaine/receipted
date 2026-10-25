/* Talks to the Receipted API. The base URL and the public demo token live in public/config.js so they can change
   without a rebuild. */
export type Item = { name: string; qty: number | null; unit_price: number | null; line_total: number | null; confidence: string | null; raw_line: string | null }
export type Issue = { type: string; severity: "high" | "medium" | "low"; message: string; receipt_line: string | null; clause_id: string | null; price_item: string | null; evidence: Record<string, unknown> | null }
export type Decision = "approve" | "needs_review" | "reject"
export type Result = {
  job_id?: string; claim_id: string; submitter: string; purpose: string; claimed_amount: number | null
  decision: Decision; decision_reason: string; currency: string | null; receipt_total: number | null; readability: string | null
  items: Item[]; verified_issues: Issue[]; dropped_by_verifier: number; draft: string
  total_cost_usd: number; total_seconds: number; model: string
  emailed?: boolean
  trace?: { node: string; seconds: number; cached: boolean | null }[]
  human?: { decision: Decision; note: string; reviewer: string; at?: string } | null
  thread?: { role: "approver" | "claimant"; name: string; text: string; at: string }[]
}
/** Whose turn it is on a held claim: the approver asked and the claimant hasn't answered yet. */
export const waitingForClaimant = (r: Result) => !!r.thread?.length && r.thread[r.thread.length - 1].role === "approver"
export const hasAnswer = (r: Result) => !!r.thread?.length && r.thread[r.thread.length - 1].role === "claimant"
export type ClaimInput = { submitter: string; purpose: string; amount: number; items: { name: string; qty: number; line_total: number | null }[]; email?: string }

declare global { interface Window { RECEIPTED_CONFIG?: { apiBase: string; demoToken: string } } }
const cfg = () => window.RECEIPTED_CONFIG ?? { apiBase: "", demoToken: "" }

export class ApiError extends Error { status: number; constructor(status: number, message: string) { super(message); this.status = status } }

async function call<T>(path: string, init: RequestInit = {}): Promise<{ status: number; body: T }> {
  const r = await fetch(cfg().apiBase + path, { ...init, headers: { "X-Api-Token": cfg().demoToken, ...(init.headers || {}) } })
  let body: unknown = null
  try { body = await r.json() } catch { /* no body */ }
  if (!r.ok && r.status !== 202) {
    const detail = (body as { detail?: string; error?: string } | null)
    throw new ApiError(r.status, detail?.detail || detail?.error || `the server answered ${r.status}`)
  }
  return { status: r.status, body: body as T }
}

/** Fire-and-forget: loads the embedding model on the server while the visitor is still filling in the form. */
export function warmUp() { fetch(cfg().apiBase + "/health?warm=1").catch(() => {}) }

export async function submitClaim(image: Blob, filename: string, claim: ClaimInput): Promise<{ jobId: string | null; result: Result | null }> {
  const fd = new FormData()
  fd.append("image", image, filename)
  fd.append("claim", JSON.stringify(claim))
  const r = await call<Result & { job_id: string }>("/check", { method: "POST", body: fd })
  if (r.status === 202) return { jobId: r.body.job_id, result: null }
  return { jobId: null, result: r.body }
}

/** Polls until the job is done. Resolves with the result; rejects if the job failed or took too long. */
export async function waitForJob(jobId: string, onTick?: (secs: number) => void): Promise<Result> {
  const start = Date.now()
  for (let i = 0; i < 70; i++) {
    await new Promise(res => setTimeout(res, i < 4 ? 2500 : 3000))
    onTick?.((Date.now() - start) / 1000)
    const r = await call<Result & { error?: string }>(`/jobs/${jobId}`)
    if (r.status === 200) return { ...r.body, job_id: jobId }
  }
  throw new ApiError(504, "the check took too long; please try again")
}

export const getJob = (jobId: string) => call<Result>(`/jobs/${jobId}`).then(r => (r.status === 200 ? { ...r.body, job_id: jobId } : null))
export const getJobImage = (jobId: string) => call<{ data_url: string }>(`/jobs/${jobId}/image`).then(r => r.body.data_url)
export const getInbox = () => call<{ pending: Result[]; decided: Result[] }>("/inbox").then(r => r.body)
export const ask = (jobId: string, question: string, reviewer: string) =>
  call<Result>(`/jobs/${jobId}/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, reviewer }) }).then(r => ({ ...r.body, job_id: jobId }))
export const answer = (jobId: string, text: string) =>
  call<Result>(`/jobs/${jobId}/answer`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answer: text }) }).then(r => ({ ...r.body, job_id: jobId }))
export const decide = (jobId: string, decision: "approve" | "reject", note: string, reviewer: string) =>
  call<Result>(`/jobs/${jobId}/decide`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision, note, reviewer }) }).then(r => r.body)
