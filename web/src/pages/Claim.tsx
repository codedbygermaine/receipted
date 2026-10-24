import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ImagePlus, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError, submitClaim, waitForJob, warmUp, type ClaimInput } from "@/lib/api"
import { SAMPLES, sampleImage, sampleThumb, type Sample } from "@/lib/samples"
import { rememberResult } from "@/pages/Verdict"

export default function Claim() {
  const nav = useNavigate()
  const [sample, setSample] = useState<Sample | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [purpose, setPurpose] = useState("")
  const [amount, setAmount] = useState("")
  const [who, setWho] = useState("")
  const [busy, setBusy] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => { warmUp() }, [])   // the server loads its model while the visitor fills in the form

  function pickSample(s: Sample) {
    setSample(s); setFile(null); setPreview(sampleImage(s))
    setPurpose(s.claim.purpose); setAmount(String(s.claim.amount))
  }
  function pickFile(f: File) {
    if (!/^image\/(jpeg|png)$/.test(f.type)) { toast.error("Please use a JPG or PNG photo."); return }
    if (f.size > 8 * 1024 * 1024) { toast.error("That photo is over 8 MB. Please use a smaller one."); return }
    setSample(null); setFile(f); setPreview(URL.createObjectURL(f))
  }
  const currency = sample?.currency ?? null
  const ready = !!preview && Number(amount) > 0

  async function submit() {
    const claim: ClaimInput = {
      submitter: who.trim() || "A member", purpose: purpose.trim(), amount: Number(amount),
      items: sample ? sample.claim.items : [],   // the sample claims carry their items so the quantity checks have something to check
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

      <Step n={1} title="Your receipt" />
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        {SAMPLES.map(s => (
          <button key={s.id} type="button" onClick={() => pickSample(s)} aria-pressed={sample?.id === s.id}
            className={`group relative overflow-visible rounded-lg border bg-card text-left transition-colors hover:border-foreground/30 focus-visible:outline-2 focus-visible:outline-ring ${sample?.id === s.id ? "border-foreground bg-muted/40" : ""}`}>
            <img src={sampleThumb(s)} alt="" className="aspect-[4/5] w-full rounded-t-lg object-cover object-top" />
            {/* the full receipt, readable, while the pointer rests on the card */}
            <img src={sampleImage(s)} alt="" className="pointer-events-none absolute left-1/2 top-1/2 z-30 hidden w-[280px] max-w-[80vw] -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-white shadow-2xl group-hover:block" />
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
        className={`mt-3 flex cursor-pointer items-center gap-3 rounded-lg border border-dashed px-4 py-3 text-sm transition-colors focus-within:outline-2 focus-within:outline-ring ${dragging ? "border-primary bg-muted" : "hover:bg-muted/60"} ${file ? "border-foreground" : ""}`}>
        <input ref={fileInput} type="file" accept="image/jpeg,image/png" className="sr-only" onChange={e => e.target.files?.[0] && pickFile(e.target.files[0])} />
        {file && preview ? <img src={preview} alt="" className="h-12 w-9 rounded object-cover object-top" /> : <ImagePlus className="size-5 shrink-0 text-foreground/60" />}
        <div>
          <div className="font-medium">{file ? file.name : "Or drop a photo of your own receipt"}</div>
          <div className="text-xs text-foreground/60">JPG or PNG, up to 8 MB</div>
        </div>
      </label>
      {file && <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">This is a public demo. Your photo will be visible in the treasurer inbox for seven days, so cover card numbers and names first.</p>}

      <Step n={2} title="What you're claiming" />
      <Card>
        <CardContent className="grid gap-5 p-5 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="purpose">What was it for?</Label>
            <Input id="purpose" value={purpose} onChange={e => setPurpose(e.target.value)} placeholder="e.g. Team lunch, 3 people" />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="amount">Amount</Label>
            <div className="relative">
              <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-foreground/60">{currency === "IDR" ? "Rp" : "$"}</span>
              <Input id="amount" type="number" inputMode="decimal" step="0.01" min="0" value={amount} onChange={e => setAmount(e.target.value)} placeholder="0.00" className={currency === "IDR" ? "pl-9" : "pl-7"} />
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="who">Your name</Label>
            <Input id="who" value={who} onChange={e => setWho(e.target.value)} placeholder="Optional" />
          </div>
        </CardContent>
      </Card>

      <Step n={3} title="Check it" />
      <div className="flex flex-wrap items-center gap-4">
        <Button size="lg" disabled={!ready || busy} onClick={submit}>
          {busy ? <><Loader2 className="size-4 animate-spin" /> Checking…</> : "Check my claim"}
        </Button>
        {busy && <span className="text-sm text-foreground/70" aria-live="polite">{stage}</span>}
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
