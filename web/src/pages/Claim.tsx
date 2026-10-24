import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ChevronDown, ImagePlus, Loader2, Plus, X } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ApiError, submitClaim, waitForJob, warmUp, type ClaimInput } from "@/lib/api"
import { SAMPLES, sampleImage, sampleThumb, type Sample } from "@/lib/samples"
import { rememberResult } from "@/pages/Verdict"

type Row = { name: string; qty: string; total: string }
const toRows = (s: Sample): Row[] => s.claim.items.map(i => ({ name: i.name, qty: String(i.qty), total: i.line_total == null ? "" : String(i.line_total) }))

export default function Claim() {
  const nav = useNavigate()
  const [sample, setSample] = useState<Sample | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [zoom, setZoom] = useState(false)
  const [purpose, setPurpose] = useState("")
  const [amount, setAmount] = useState("")
  const [who, setWho] = useState("")
  const [rows, setRows] = useState<Row[]>([])
  const [itemsOpen, setItemsOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => { warmUp() }, [])   // the server loads its model while the visitor fills in the form

  function pickSample(s: Sample) {
    setSample(s); setFile(null); setPreview(sampleImage(s))
    setPurpose(s.claim.purpose); setAmount(String(s.claim.amount)); setWho(s.claim.submitter); setRows(toRows(s)); setItemsOpen(false)
  }
  function pickFile(f: File) {
    if (!/^image\/(jpeg|png)$/.test(f.type)) { toast.error("Please use a JPG or PNG photo."); return }
    if (f.size > 8 * 1024 * 1024) { toast.error("That photo is over 8 MB. Please use a smaller one."); return }
    setSample(null); setFile(f); setPreview(URL.createObjectURL(f)); setRows([]); setItemsOpen(false)
  }
  const currency = sample?.currency ?? null
  const ready = !!preview && Number(amount) > 0

  async function submit() {
    const claim: ClaimInput = {
      submitter: who.trim() || "A member", purpose: purpose.trim(), amount: Number(amount),
      items: rows.filter(r => r.name.trim()).map(r => ({ name: r.name.trim(), qty: r.qty === "" ? 1 : Number(r.qty), line_total: r.total === "" ? null : Number(r.total) })),
    }
    setBusy(true); setElapsed(0)
    const timer = setInterval(() => setElapsed(e => e + 1), 1000)
    try {
      const blob: Blob = file ?? (await fetch(sampleImage(sample!)).then(r => r.blob()))
      const first = await submitClaim(blob, file ? file.name : `${sample!.id}.jpg`, claim)
      const result = first.result ?? (await waitForJob(first.jobId!))
      rememberResult(result, preview!)
      nav(`/claim/${result.job_id ?? "latest"}`)
    } catch (e) {
      const err = e as ApiError
      console.error(err)
      toast.error(err.status === 429 ? "The demo has used up today's budget. Please try again tomorrow." : "Something went wrong on our side. Please try again in a moment.")
      setBusy(false)
    } finally { clearInterval(timer) }
  }

  const stage = elapsed < 8 ? "Reading your receipt…" : elapsed < 16 ? "Checking it against the policy…" : elapsed < 24 ? "Writing your reply…" : "Nearly there. The first check of the day takes longer while the checker wakes up."

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Claim an expense</h1>
      <p className="mt-1 text-foreground/70">Three steps, about ten seconds. The first check of the day takes a little longer.</p>

      <Step n={1} title="Your receipt" />
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        {SAMPLES.map(s => (
          <button key={s.id} type="button" onClick={() => pickSample(s)} aria-pressed={sample?.id === s.id}
            className={`group overflow-hidden rounded-lg border bg-card text-left transition-all hover:border-foreground/30 focus-visible:outline-2 focus-visible:outline-ring ${sample?.id === s.id ? "ring-2 ring-primary border-transparent" : ""}`}>
            <img src={sampleThumb(s)} alt="" className="aspect-[4/5] w-full object-cover object-top" />
            <div className="p-2 leading-tight">
              <div className="text-xs font-medium">{s.title}</div>
              <div className="mt-0.5 text-xs text-foreground/60">{s.where}</div>
            </div>
          </button>
        ))}
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto]">
        <label
          onDragOver={e => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)}
          onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) pickFile(f) }}
          className={`flex cursor-pointer items-center gap-3 rounded-lg border border-dashed px-4 py-3 text-sm transition-colors focus-within:outline-2 focus-within:outline-ring ${dragging ? "border-primary bg-muted" : "hover:bg-muted/60"} ${file ? "border-primary" : ""}`}>
          <input ref={fileInput} type="file" accept="image/jpeg,image/png" className="sr-only" onChange={e => e.target.files?.[0] && pickFile(e.target.files[0])} />
          <ImagePlus className="size-5 shrink-0 text-foreground/60" />
          <div>
            <div className="font-medium">{file ? `Using ${file.name}` : "Or drop a photo of your own receipt"}</div>
            <div className="text-xs text-foreground/60">JPG or PNG, up to 8 MB</div>
          </div>
        </label>
        {preview && (
          <button type="button" onClick={() => setZoom(true)} aria-label="Enlarge the chosen receipt" className="flex items-center gap-3 rounded-lg border bg-card p-2 text-left text-sm hover:border-foreground/30">
            <img src={preview} alt="" className="h-16 w-12 rounded object-cover object-top" />
            <div><div className="font-medium">{sample ? sample.title : "Your photo"}</div><div className="text-xs text-foreground/60">Tap to read it</div></div>
          </button>
        )}
      </div>
      {file && <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">This is a public demo. Your photo will be visible in the treasurer inbox for seven days, so cover card numbers and names first.</p>}
      <Dialog open={zoom} onOpenChange={setZoom}>
        <DialogContent className="max-h-[92vh] max-w-3xl overflow-auto p-2"><DialogTitle className="sr-only">Receipt photo, enlarged</DialogTitle>{preview && <img src={preview} alt="Receipt photo, enlarged" className="w-full" />}</DialogContent>
      </Dialog>

      <Step n={2} title="What you're claiming" />
      <Card>
        <CardContent className="grid gap-5 p-5 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="purpose">What was it for?</Label>
            <Input id="purpose" value={purpose} onChange={e => setPurpose(e.target.value)} placeholder="e.g. Team lunch, 3 people" />
            <p className="text-xs text-foreground/60">For meals, say how many people. The policy has a limit per person.</p>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="amount">Amount {currency ? `(${currency})` : ""}</Label>
            <Input id="amount" type="number" inputMode="decimal" step="0.01" min="0" value={amount} onChange={e => setAmount(e.target.value)} placeholder="0.00" />
            <p className="text-xs text-foreground/60">{currency ? "The sample receipts are in this currency." : "In the receipt's currency."}</p>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="who">Your name</Label>
            <Input id="who" value={who} onChange={e => setWho(e.target.value)} placeholder="So the reply can be addressed to you" />
          </div>
          <div className="sm:col-span-2">
            <Collapsible open={itemsOpen} onOpenChange={setItemsOpen}>
              <CollapsibleTrigger className="-mx-1 flex items-center gap-1 rounded px-1 py-1.5 text-sm font-medium text-foreground/70 hover:text-foreground">
                <ChevronDown className={`size-4 transition-transform ${itemsOpen ? "rotate-180" : ""}`} />
                {rows.length ? `Items you're claiming (${rows.length})` : "Add the items you're claiming"} <span className="font-normal">· optional</span>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-3">
                <p className="mb-3 text-xs text-foreground/60">Listing items lets the checker confirm each one is on the receipt and the quantities match. Skip it to check the total only.</p>
                <div className="grid gap-2">
                  <div className="grid grid-cols-[1fr_64px_96px_32px] gap-2 px-1 text-xs font-medium text-foreground/60"><span>Item</span><span className="text-right">Qty</span><span className="text-right">Total</span><span /></div>
                  {rows.map((r, i) => (
                    <div key={i} className="grid grid-cols-[1fr_64px_96px_32px] items-center gap-2">
                      <Input value={r.name} aria-label="Item" placeholder="Item" onChange={e => setRows(rs => rs.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} />
                      <Input value={r.qty} aria-label="Quantity" inputMode="numeric" className="text-right" onChange={e => setRows(rs => rs.map((x, j) => j === i ? { ...x, qty: e.target.value } : x))} />
                      <Input value={r.total} aria-label="Line total" inputMode="decimal" className="text-right" onChange={e => setRows(rs => rs.map((x, j) => j === i ? { ...x, total: e.target.value } : x))} />
                      <Button variant="ghost" size="icon" aria-label="Remove item" onClick={() => setRows(rs => rs.filter((_, j) => j !== i))}><X className="size-4" /></Button>
                    </div>
                  ))}
                  <div><Button variant="outline" size="sm" onClick={() => setRows(rs => [...rs, { name: "", qty: "1", total: "" }])}><Plus className="size-4" /> Add an item</Button></div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          </div>
        </CardContent>
      </Card>

      <Step n={3} title="Check it" />
      <div className="flex flex-wrap items-center gap-4">
        <Button size="lg" disabled={!ready || busy} onClick={submit}>
          {busy ? <><Loader2 className="size-4 animate-spin" /> Checking…</> : "Check my claim"}
        </Button>
        <span className="text-sm text-foreground/70" aria-live="polite">
          {busy ? stage : !preview ? "Pick a receipt first." : !(Number(amount) > 0) ? "Enter the amount you're claiming." : "You'll get the answer here. A treasurer only hears about it if something needs a person."}
        </span>
      </div>
    </div>
  )
}

function Step({ n, title }: { n: number; title: string }) {
  return (
    <div className="mb-3 mt-8 flex items-center gap-2 text-base font-semibold">
      <span className="grid size-6 place-items-center rounded-full bg-foreground text-xs font-medium text-background">{n}</span>{title}
    </div>
  )
}
