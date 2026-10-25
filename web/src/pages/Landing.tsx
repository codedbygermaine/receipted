import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export default function Landing() {
  return (
    <div className="mx-auto max-w-2xl py-6 sm:py-14">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Receipted checks expense claims against receipts and an expense policy.</h1>
      <p className="mt-4 text-lg text-foreground/70">Before a claim is paid, someone checks that there is a receipt, that the amount matches it and that the policy allows it. Receipted does that in seconds and shows its reasons.</p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button asChild size="lg"><Link to="/claim">Submit a claim</Link></Button>
        <Button asChild variant="outline" size="lg"><Link to="/inbox">Approve claims</Link></Button>
      </div>
      <p className="mt-8 text-sm"><Link to="/about" className="text-foreground/70 underline underline-offset-2 hover:text-foreground">How it works</Link></p>
    </div>
  )
}
