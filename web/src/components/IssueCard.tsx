import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { Issue } from "@/lib/api"
import { SEVERITY, clauseText, issueTitle } from "@/lib/format"

const TONE = { no: "border-l-red-500", hold: "border-l-amber-500", note: "border-l-slate-400" }
const BADGE = { no: "bg-red-50 text-red-700 border-red-200", hold: "bg-amber-50 text-amber-800 border-amber-200", note: "bg-slate-100 text-slate-700 border-slate-200" }

/** One problem, in words a member can act on. The clause sits behind "Show the rule"; internal evidence stays
    hidden. `resolved` is for claims a treasurer has already decided: the badge then says so instead of asking
    for confirmation. Hovering or tapping the card tells the parent which receipt line to highlight. */
export function IssueCard({ issue, also = [], resolved = false, onPoint }:
  { issue: Issue; also?: string[]; resolved?: boolean; onPoint?: (line: string | null) => void }) {
  const [open, setOpen] = useState(false)
  const sev = SEVERITY[issue.severity]
  const clause = clauseText(issue)
  return (
    <div className={`rounded-lg border border-l-4 bg-card p-4 ${resolved ? "border-l-slate-300" : TONE[sev.tone]}`}
      onMouseEnter={() => onPoint?.(issue.receipt_line)} onMouseLeave={() => onPoint?.(null)} onClick={() => onPoint?.(issue.receipt_line)}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="font-medium">{issueTitle(issue)}</div>
        <Badge variant="outline" className={resolved ? BADGE.note : BADGE[sev.tone]}>{resolved ? "Settled by the treasurer" : sev.label}</Badge>
      </div>
      <p className="mt-1.5 text-sm text-foreground/90">{issue.message}</p>
      {also.map((m, k) => <p key={k} className="mt-1 text-sm text-foreground/70">{m}</p>)}
      {issue.receipt_line && (
        <p className="mt-2 text-xs text-foreground/70">On the receipt: <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground">{issue.receipt_line}</code></p>
      )}
      {clause && (
        <div className="mt-1">
          <button type="button" onClick={e => { e.stopPropagation(); setOpen(o => !o) }} className="-mx-1 inline-flex items-center gap-1 rounded px-1 py-1.5 text-sm font-medium text-foreground/70 hover:text-foreground">
            <ChevronDown className={`size-4 transition-transform ${open ? "rotate-180" : ""}`} /> {open ? "Hide the rule" : "Show the rule"}
          </button>
          {open && <p className="mt-1 rounded-md bg-muted/70 p-3 text-sm leading-relaxed text-foreground/80"><span className="font-medium text-foreground">{issue.clause_id ? `Rule ${issue.clause_id}. ` : ""}</span>{clause}</p>}
        </div>
      )}
    </div>
  )
}
