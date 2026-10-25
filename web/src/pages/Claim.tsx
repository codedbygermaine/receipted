import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ImagePlus, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError, submitClaim, waitForJob, warmUp, type ClaimInput } from "@/lib/api"
import { SAMPLES, sampleImage, sampleThumb, type Sample } from "@/lib/samples"
import { rememberResult } from "@/pages/Verdict"
import { Lightbox } from "@/components/ClaimReview"

export default function Claim() {
  const nav = useNavigate()
  const [sample, setSample] = useState<Sample | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [purpose, setPurpose] = useState("")
  const [amount, setAmount] = useState("")
  const [who, setWho] = useState("")
  const [email, setEmail] = useState("")
  const [people, setPeople] = useState("")
  const [busy, setBusy] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [hovered, setHovered] = useState<Sample | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const amountInput = useRef<HTMLInputElement>(null)
  const whoInput = useRef<HTMLInputElement>(null)
  const lightbox = useRef<HTMLDialogElement>(null)

  useEffect(() => { warmUp() }, [])   // the server loads its model while the visitor fills in the form

  function pickSample(s: Sample) {
    setSample(s); setFile(null); setPreview(sampleImage(s)); setHovered(null)
    const m = s.claim.purpose.match(/(\d+) people/)
    setPurpose(s.claim.purpose.replace(/,\s*\d+ people/, "")); setPeople(m ? m[1] : "")
    setAmount(s.currency === "IDR" ? String(s.claim.amount) : s.claim.amount.toFixed(2))
  }
  function pickFile(f: File) {
    if (!/^image\/(jpeg|png)$/.test(f.type)) { toast("JPG or PNG only."); return }
    if (f.size > 8 * 1024 * 1024) { toast("Photos up to 8 MB."); return }
    setSample(null); setFile(f); setPreview(URL.createObjectURL(f))
  }
  const currency = sample?.currency ?? null

  async function submit() {
    if (!preview) { toast("Pick a receipt first."); return }
    if (!(Number(amount) > 0)) { amountInput.current?.focus(); return }
    if (!who.trim()) { whoInput.current?.focus(); toast("Add your name so the reply can be addressed to you."); return }
    const claim: ClaimInput = {
      submitter: who.trim(), email: email.trim() || undefined, purpose: people.trim() ? `${purpose.trim()}, ${people.trim()} people` : purpose.trim(), amount: Number(amount),
      items: sample ? sample.claim.items : [],   // the sample claims carry their items so the quantity checks have something to check
    }
    setBusy(true); setElapsed(0)
    const timer = setInterval(() => setElapsed(e => e + 1), 1000)
    try {
      const blob: Blob = file ?? (await fetch(sampleImage(sample!)).then(r => r.blob()))
      const first = await submitClaim(blob, file ? file.name : `${sample!.id}.jpg`, claim)
      const result = first.result ?? (await waitForJob(first.jobId!))
      rememberResult(result, preview)
      nav(`/claim/${result.job_id ?? "latest"}`)
    } catch (e) {
      const err = e as ApiError
      console.error(err)
      toast(err.status === 429 ? "The demo has used up today's budget. Try again tomorrow." : "The check didn't run. Try again in a moment.")
      setBusy(false)
    } finally { clearInterval(timer) }
  }

  const stage = elapsed < 8 ? "Reading your receipt…" : elapsed < 16 ? "Checking it against the policy…" : "Writing your reply…"

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Submit a claim</h1>

      <h2 className="mb-3 mt-8 text-base font-semibold">Sample receipts</h2>
      <div role="radiogroup" aria-label="Sample receipts" className="relative grid grid-cols-3 gap-3 sm:grid-cols-6" onMouseLeave={() => setHovered(null)}>
        {/* the full receipt, readable, while the pointer rests on a card; centred over the grid so it never runs off the page */}
        {hovered && <img src={sampleImage(hovered)} alt="" className="pointer-events-none absolute left-1/2 top-0 z-30 w-[280px] max-w-[90%] -translate-x-1/2 rounded-lg border bg-white shadow-2xl" />}
        {SAMPLES.map(s => (
          <button key={s.id} type="button" role="radio" aria-checked={sample?.id === s.id} onClick={() => pickSample(s)} onMouseEnter={() => setHovered(s)} onFocus={() => setHovered(s)} onBlur={() => setHovered(null)}
            className={`rounded-lg border bg-card text-left transition-colors hover:border-foreground/30 ${sample?.id === s.id ? "border-foreground bg-muted/40" : ""}`}>
            <img src={sampleThumb(s)} alt="" title={s.credit} className="aspect-[4/5] w-full rounded-t-lg object-cover object-top" />
            <div className="p-2 leading-tight">
              <div className="text-xs font-medium">{s.title}</div>
              <div className="mt-0.5 text-xs text-foreground/60">{s.where}</div>
            </div>
          </button>
        ))}
      </div>

      <label
        onDragOver={e => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) pickFile(f) }}
        className={`mt-3 flex cursor-pointer items-center gap-3 rounded-lg border border-dashed px-4 py-3 text-sm transition-colors focus-within:outline-2 focus-within:outline-ring ${dragging ? "border-foreground bg-muted" : "hover:bg-muted/60"} ${file ? "border-foreground" : ""}`}>
        <input ref={fileInput} type="file" accept="image/jpeg,image/png" className="sr-only" onChange={e => e.target.files?.[0] && pickFile(e.target.files[0])} />
        {preview ? (
          <button type="button" onClick={e => { e.preventDefault(); lightbox.current?.showModal() }} aria-label="Enlarge the chosen receipt" className="shrink-0 cursor-zoom-in"><img src={preview} alt="" className="h-12 w-9 rounded object-cover object-top" /></button>
        ) : <ImagePlus className="size-5 shrink-0 text-foreground/60" />}
        <div>
          <div className="font-medium">{file ? file.name : "Upload a receipt"}</div>
          <div className="text-xs text-foreground/60">JPG or PNG, up to 8 MB</div>
        </div>
      </label>
      <Lightbox ref={lightbox} src={preview} />
      {file && <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">This is a public demo. Your photo will be visible in the approvals inbox for seven days, so cover card numbers and names first.</p>}

      <h2 className="mb-3 mt-8 text-base font-semibold">{sample ? "Sample claim" : "Your claim"}</h2>
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor="purpose">Business purpose</Label>
          <Input id="purpose" value={purpose} onChange={e => setPurpose(e.target.value)} placeholder="e.g. Team lunch" />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="amount">Amount{currency ? ` (${currency})` : ""}</Label>
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-foreground/60">{currency === "IDR" ? "Rp" : "$"}</span>
            <Input ref={amountInput} id="amount" type="number" inputMode="decimal" step="0.01" min="0" value={amount} onChange={e => setAmount(e.target.value)} placeholder="0.00" className={currency === "IDR" ? "pl-9" : "pl-7"} />
          </div>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="who">Your name</Label>
          <Input ref={whoInput} id="who" value={who} onChange={e => setWho(e.target.value)} />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="email">Email <span className="font-normal text-foreground/60">(to hear back)</span></Label>
          <Input id="email" type="email" inputMode="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="people">People <span className="font-normal text-foreground/60">(for meals)</span></Label>
          <Input id="people" inputMode="numeric" value={people} onChange={e => setPeople(e.target.value.replace(/\D/g, ""))} className="w-24" />
        </div>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button size="lg" disabled={busy} onClick={submit}>
          {busy ? <><Loader2 className="size-4 animate-spin motion-reduce:animate-none" /> Checking…</> : "Check my claim"}
        </Button>
        {busy && <span className="text-sm text-foreground/70" aria-live="polite">{stage}</span>}
      </div>
    </div>
  )
}
