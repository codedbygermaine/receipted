import { useState } from "react"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Item } from "@/lib/api"
import { money } from "@/lib/format"

const norm = (s: string | null | undefined) => (s || "").replace(/\s+/g, " ").trim().toLowerCase()

/** The receipt photo beside the lines read from it. Promo and discount lines are dimmed; a line is only marked
    when it was hard to read. The highlighted row is the one an issue card is pointing at. */
export function ReceiptPanel({ src, items, total, currency, readability, highlight }:
  { src: string | null; items: Item[]; total: number | null; currency: string | null; readability: string | null; highlight?: string | null }) {
  const [zoom, setZoom] = useState(false)
  const unsure = items.filter(i => i.confidence && i.confidence !== "high").length
  const anyQty = items.some(i => i.qty != null)
  return (
    <div className="grid gap-4 sm:grid-cols-[180px_1fr]">
      <div>
        {src ? (
          <button type="button" onClick={() => setZoom(true)} aria-label="Enlarge the receipt" className="block w-full cursor-zoom-in rounded-lg border bg-white focus-visible:outline-2 focus-visible:outline-ring">
            <img src={src} alt="Receipt photo" className="w-full rounded-lg object-contain" />
          </button>
        ) : <div className="aspect-[3/4] w-full animate-pulse rounded-lg bg-muted" />}
        <Dialog open={zoom} onOpenChange={setZoom}>
          <DialogContent className="max-h-[92vh] max-w-3xl overflow-auto p-2">
            <DialogTitle className="sr-only">Receipt photo, enlarged</DialogTitle>
            {src && <img src={src} alt="Receipt photo, enlarged" className="w-full" />}
          </DialogContent>
        </Dialog>
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
          <div><span className="text-foreground/70">Receipt total</span> <span className="font-semibold">{money(total, currency)}</span></div>
          <div className="text-xs text-foreground/60">{items.length} lines read{readability && readability !== "clear" ? ` · photo ${readability}` : ""}{unsure ? ` · ${unsure} hard to read` : ""}</div>
        </div>
        <Table className="mt-2 text-sm">
          <TableHeader><TableRow>{anyQty && <TableHead className="w-10 text-right">Qty</TableHead>}<TableHead>Item</TableHead><TableHead className="text-right">Total</TableHead></TableRow></TableHeader>
          <TableBody>
            {items.map((it, i) => {
              const promo = (it.line_total ?? 0) < 0 || /buy \d get|discount|promo/i.test(it.name)
              const hi = !!highlight && norm(it.raw_line) === norm(highlight)
              return (
                <TableRow key={i} className={`${hi ? "bg-amber-100/70" : ""} ${promo ? "text-foreground/60" : ""}`} title={it.raw_line || undefined}>
                  {anyQty && <TableCell className="text-right tabular-nums">{it.qty ?? ""}</TableCell>}
                  <TableCell className="whitespace-normal break-words">{it.name}{it.confidence && it.confidence !== "high" ? <span className="ml-2 rounded bg-amber-50 px-1.5 py-0.5 text-xs font-medium text-amber-800">hard to read</span> : null}</TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">{money(it.line_total, null)}</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
