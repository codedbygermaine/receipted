import { useEffect, useRef, useState } from "react"
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
    <div className="grid grid-cols-[96px_1fr] gap-4 sm:grid-cols-[200px_1fr] sm:gap-6">
      <Photo src={image} />
      <div className="min-w-0">
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-foreground/60">Receipt total</span>
          <span className="tabular-nums">{money(r.receipt_total, r.currency)}</span>
        </div>
        {rows.length > 0 ? (
          <div className="mt-3 divide-y border-y">
            {rows.map(({ g, item }, k) => <Flagged key={k} issue={g.issue} also={g.also} item={item} currency={r.currency} muted={muted} />)}
          </div>
        ) : (
          <p className="mt-3 text-sm text-foreground/70">No rule broken. A line was hard to read.</p>
        )}
        {rest.length > 0 && (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer py-1 text-foreground/60 hover:text-foreground">{rows.length ? "Other lines" : "Lines read"}</summary>
            <ul className="mt-1 divide-y">
              {rest.map((it, i) => <li key={i} className={`flex justify-between gap-4 py-1.5 ${(it.line_total ?? 0) < 0 ? "text-foreground/60" : "text-foreground/80"}`}><span className="min-w-0 break-words">{it.name}{it.confidence && it.confidence !== "high" ? <span className="ml-2 text-xs text-foreground/60">hard to read</span> : null}</span><span className="shrink-0 text-xs tabular-nums">{money(it.line_total, null)}</span></li>)}
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
        {item && <span className="shrink-0 text-sm tabular-nums">{money(item.line_total, currency)}</span>}
      </div>
      <p className="mt-1 text-sm text-foreground/80">{tidyMessage(issue.message, item?.name)}</p>
      {also.map((m, k) => <p key={k} className="mt-1 text-sm text-foreground/60">{tidyMessage(m, item?.name)}</p>)}
      {clause && (
        <div className="mt-1">
          <button type="button" onClick={() => setOpen(o => !o)} className="-my-1 py-1 text-xs text-foreground/60 underline-offset-2 hover:text-foreground hover:underline">{open ? "Hide the rule" : `Rule ${issue.clause_id || ""}`.trim()}</button>
          {open && <p className="mt-1.5 text-sm leading-relaxed text-foreground/70">{clause}</p>}
        </div>
      )}
    </div>
  )
}

/** The receipt photo; click opens it full size in a real dialog (Escape closes, focus is trapped by the platform). */
export function Photo({ src, className = "" }: { src: string | null; className?: string }) {
  const dlg = useRef<HTMLDialogElement>(null)
  if (!src) return <div className="aspect-[3/4] w-full animate-pulse rounded-md bg-muted" />
  return (
    <div className={className}>
      <button type="button" onClick={() => dlg.current?.showModal()} aria-label="Enlarge the receipt" className="block w-full cursor-zoom-in rounded-md">
        <img src={src} alt="Receipt photo" className="w-full rounded-md border bg-white" />
      </button>
      <Lightbox ref={dlg} src={src} />
    </div>
  )
}

export function Lightbox({ ref, src }: { ref: React.RefObject<HTMLDialogElement | null>; src: string | null }) {
  useEffect(() => { if (!src) ref.current?.close() }, [src, ref])
  return (
    <dialog ref={ref} onClick={e => { if (e.target === e.currentTarget) e.currentTarget.close() }}
      className="m-auto max-h-dvh max-w-[100vw] cursor-zoom-out bg-transparent p-4 backdrop:bg-black/60">
      {src && <img src={src} alt="Receipt photo, enlarged" className="enter max-h-[92dvh] max-w-full rounded-md bg-white" />}
    </dialog>
  )
}
