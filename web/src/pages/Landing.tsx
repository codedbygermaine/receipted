import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export default function Landing() {
  return (
    <div className="mx-auto max-w-2xl py-6 sm:py-14">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">An expense reviewer that shows its working.</h1>
      <p className="mt-4 text-lg text-foreground/70">Upload a receipt and enter the amount. Receipted checks the expense rules, points at the receipt line and the rule behind any problem, and says whether the claim is approved, needs an approver or can't be paid.</p>
      <p className="mt-4 text-foreground/70">A SGD 104.72 lunch for two matches its receipt. It is also SGD 52.36 a person, above the SGD 40 limit, so it goes to an approver with the receipt and the rule side by side.</p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button asChild size="lg"><Link to="/claim">Try a sample claim</Link></Button>
        <Button asChild variant="outline" size="lg"><Link to="/inbox">Review a claim</Link></Button>
      </div>
      <p className="mt-8 text-sm"><Link to="/about" className="text-foreground/70 underline underline-offset-2 hover:text-foreground">How it works</Link></p>
    </div>
  )
}
