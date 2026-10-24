/* Turns the API's internal vocabulary into words a member or treasurer would use. */
import type { Decision, Issue } from "./api"

export function money(v: number | null | undefined, cur: string | null | undefined) {
  if (v == null) return "—"
  const c = cur || ""
  const n = c === "IDR" || c === "JPY" ? Math.round(v).toLocaleString() : v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return c ? `${c} ${n}` : n
}

export const DECISION: Record<Decision, { label: string; tone: "ok" | "hold" | "no" }> = {
  approve: { label: "Approved", tone: "ok" },
  needs_review: { label: "A treasurer needs to look", tone: "hold" },
  reject: { label: "Can't be paid as filed", tone: "no" },
}

export const SEVERITY: Record<Issue["severity"], { label: string; tone: "no" | "hold" | "note" }> = {
  high: { label: "Can't be paid", tone: "no" },
  medium: { label: "Needs confirming", tone: "hold" },
  low: { label: "Worth knowing", tone: "note" },
}

const TITLES: Record<string, string> = {
  claim_exceeds_receipt: "Claimed more than the receipt total",
  claim_below_receipt: "Claimed less than the receipt total",
  purpose_missing: "No purpose given",
  claim_lines_vs_amount: "Items don't add up to the amount claimed",
  claimed_item_not_on_receipt: "Claimed item isn't on the receipt",
  claimed_qty_exceeds_receipt: "Claimed more of an item than the receipt shows",
  line_arithmetic: "A line's quantity × price doesn't match",
  lines_vs_totals: "Lines don't add up to the printed total",
  totals_arithmetic: "The receipt's own totals don't add up",
  possible_personal_item: "Looks like a personal item",
  duplicate_receipt: "This receipt was already claimed",
  low_confidence_lines: "A line was hard to read",
}
export function issueTitle(i: Issue) {
  if (TITLES[i.type]) return TITLES[i.type]
  const t = i.type.replace(/_/g, " ").trim()
  return t.charAt(0).toUpperCase() + t.slice(1)
}
export const clauseText = (i: Issue) => (i.evidence?.clause_text as string | undefined) || null

export function claimTime(claimId: string): Date | null {
  const m = claimId.match(/(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/)
  if (!m) return null
  return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]))
}
export function ago(d: Date | null) {
  if (!d) return ""
  const mins = Math.max(0, Math.round((Date.now() - d.getTime()) / 60000))
  if (mins < 2) return "just now"
  if (mins < 60) return `${mins} min ago`
  const h = Math.round(mins / 60)
  if (h < 48) return `${h} h ago`
  return `${Math.round(h / 24)} days ago`
}

/** The deterministic checks and the model's rule check can both flag the same receipt line (a medicine, say).
    Showing two cards for one line reads as a bug, so issues on the same line are merged: the strongest severity
    wins, the first message leads, the others follow as extra sentences. */
export type IssueGroup = { issue: Issue; also: string[] }
const normLine = (s: string | null) => (s || "").replace(/\s+/g, " ").trim().toLowerCase()
const RANK: Record<Issue["severity"], number> = { high: 3, medium: 2, low: 1 }
export function groupIssues(issues: Issue[]): IssueGroup[] {
  const out: IssueGroup[] = []
  const byLine = new Map<string, IssueGroup>()
  for (const i of issues) {
    const key = normLine(i.receipt_line)
    if (!key) { out.push({ issue: i, also: [] }); continue }
    const g = byLine.get(key)
    if (!g) { const ng = { issue: i, also: [] }; byLine.set(key, ng); out.push(ng); continue }
    if (RANK[i.severity] > RANK[g.issue.severity]) { g.also.unshift(g.issue.message); g.issue = { ...i, evidence: i.evidence ?? g.issue.evidence } }
    else { g.also.push(i.message) }
    if (!g.issue.evidence?.clause_text && i.evidence?.clause_text) g.issue = { ...g.issue, evidence: { ...(g.issue.evidence || {}), clause_text: i.evidence.clause_text }, clause_id: g.issue.clause_id ?? i.clause_id }
  }
  return out
}

/** "API-20261024172752-7aee" → "7aee": a reference a person can read out; the full id stays in a tooltip. */
export const shortRef = (claimId: string) => claimId.split("-").pop() || claimId
