import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export default function Landing() {
  return (
    <div className="mx-auto max-w-2xl py-6 sm:py-14">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Receipted checks expense claims against the receipt and your policy.</h1>
      <p className="mt-4 text-lg text-foreground/70">Someone pays for something for work and claims it back. Before it is paid, a person has to check: is there a receipt, does the amount match, does the policy allow it. Receipted does that check in seconds and shows its reasons. For any team that reimburses expenses: a startup, a department, a club.</p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button asChild size="lg"><Link to="/claim">Submit a claim</Link></Button>
        <Button asChild variant="outline" size="lg"><Link to="/inbox">Approve claims</Link></Button>
      </div>
      <p className="mt-6 text-sm text-foreground/60">Pick one of six receipts and see what the checker says, then decide the held claims as the approver.</p>
      <p className="mt-8 text-sm"><Link to="/about" className="text-foreground/70 underline underline-offset-2 hover:text-foreground">How it works</Link></p>
    </div>
  )
}
