import { useState } from "react"
import type { Issue, Item, Result } from "@/lib/api"
import { clauseText, groupIssues, issueTitle, money, tidyMessage } from "@/lib/format"

const norm = (s: string | null | undefined) => (s || "").replace(/\s+/g, " ").trim().toLowerCase()

/** The receipt photo beside only what matters: the flagged lines, each with the sentence that explains it.
    Everything else on the receipt folds away. Shared by the member's verdict and the treasurer's inbox. */
export function ClaimReview({ r, image, muted = false }: { r: Result; image: string | null; muted?: boolean }) {
  const groups = groupIssues(r.verified_issues)
  const flaggedItems = new Set<number>()
  const rows = groups.map(g => {
    const idx = r.items.findIndex(it => g.issue.receipt_line && norm(it.raw_line) === norm(g.issue.receipt_line))
    if (idx >= 0) flaggedItems.add(idx)
    return { g, item: idx >= 0 ? r.items[idx] : null }
  })
  const rest = r.items.filter((_, i) => !flaggedItems.has(i))

  return (
    <div className="grid gap-6 sm:grid-cols-[200px_1fr]">
      <Photo src={image} />
      <div className="min-w-0">
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-foreground/60">Receipt total</span>
          <span className="font-mono tabular-nums">{money(r.receipt_total, r.currency)}</span>
        </div>
        {rows.length > 0 ? (
          <div className="mt-3 divide-y border-y">
            {rows.map(({ g, item }, k) => <Flagged key={k} issue={g.issue} also={g.also} item={item} currency={r.currency} muted={muted} />)}
          </div>
        ) : (
          <p className="mt-3 text-sm text-foreground/70">No rule was broken. A line was hard to read, so a person checks the numbers.</p>
        )}
        {rest.length > 0 && (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer py-1 text-foreground/60 hover:text-foreground">{rows.length ? `${rest.length} other line${rest.length === 1 ? "" : "s"}` : `${rest.length} line${rest.length === 1 ? "" : "s"} read`}</summary>
            <ul className="mt-1 divide-y">
              {rest.map((it, i) => <li key={i} className={`flex justify-between gap-4 py-1.5 ${(it.line_total ?? 0) < 0 ? "text-foreground/50" : "text-foreground/80"}`}><span className="min-w-0 break-words">{it.name}{it.confidence && it.confidence !== "high" ? <span className="ml-2 text-xs text-foreground/50">hard to read</span> : null}</span><span className="shrink-0 font-mono text-xs tabular-nums">{money(it.line_total, null)}</span></li>)}
            </ul>
          </details>
        )}
      </div>
    </div>
  )
}

function Flagged({ issue, also, item, currency, muted }: { issue: Issue; also: string[]; item: Item | null; currency: string | null; muted: boolean }) {
  const [open, setOpen] = useState(false)
  const clause = clauseText(issue)
  const title = item ? item.name : issueTitle(issue)
  return (
    <div className={`py-3 ${muted ? "text-foreground/70" : ""}`}>
      <div className="flex items-baseline justify-between gap-4">
        <span className="min-w-0 break-words font-medium">{title}</span>
        {item && <span className="shrink-0 font-mono text-sm tabular-nums">{money(item.line_total, currency)}</span>}
      </div>
      <p className="mt-1 text-sm text-foreground/80">{tidyMessage(issue.message, item?.name)}</p>
      {also.map((m, k) => <p key={k} className="mt-1 text-sm text-foreground/60">{tidyMessage(m, item?.name)}</p>)}
      {clause && (
        <div className="mt-1.5">
          <button type="button" onClick={() => setOpen(o => !o)} className="text-xs text-foreground/60 underline-offset-2 hover:text-foreground hover:underline">{open ? "Hide the rule" : `Rule ${issue.clause_id || ""}`.trim()}</button>
          {open && <p className="enter mt-1.5 text-sm leading-relaxed text-foreground/70">{clause}</p>}
        </div>
      )}
    </div>
  )
}

/** The receipt photo. Hover rests a readable copy over the page; click opens it full size. */
function Photo({ src }: { src: string | null }) {
  const [big, setBig] = useState(false)
  if (!src) return <div className="aspect-[3/4] w-full animate-pulse rounded-md bg-muted" />
  return (
    <div className="group relative">
      <button type="button" onClick={() => setBig(b => !b)} aria-label={big ? "Shrink the receipt" : "Enlarge the receipt"} className="block w-full">
        <img src={src} alt="Receipt photo" className="w-full rounded-md border bg-white" />
      </button>
      <img src={src} alt="" className="pointer-events-none absolute left-0 top-0 z-30 hidden w-[380px] max-w-[85vw] rounded-md border bg-white shadow-2xl group-hover:block" />
      {big && (
        <div className="fixed inset-0 z-50 flex cursor-zoom-out items-center justify-center bg-black/60 p-4" onClick={() => setBig(false)}>
          <img src={src} alt="Receipt photo, enlarged" className="enter max-h-full max-w-full rounded-md bg-white" />
        </div>
      )}
    </div>
  )
}
