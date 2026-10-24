import { Link } from "react-router-dom"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function Landing() {
  return (
    <div className="mx-auto max-w-3xl py-6 sm:py-14">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Expense claims, checked against the receipt.</h1>
      <p className="mt-3 max-w-xl text-lg text-foreground/70">Hand in a receipt and a claim. You get a clear answer in about ten seconds, and every problem it finds points at the line on the receipt and the rule behind it.</p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button asChild size="lg"><Link to="/claim">Try a claim <ArrowRight className="size-4" /></Link></Button>
        <span className="text-sm text-foreground/60">Six sample receipts to pick from, or drop a photo of your own.</span>
      </div>
      <div className="mt-12 rounded-xl border bg-card p-5 sm:flex sm:items-center sm:justify-between sm:gap-6">
        <div>
          <div className="font-medium">Treasurer?</div>
          <p className="mt-0.5 text-sm text-foreground/70">Claims the checker couldn't settle wait in an inbox, with the receipt and the reason side by side. Your decision writes the reply.</p>
        </div>
        <Button asChild variant="outline" className="mt-3 sm:mt-0 sm:shrink-0"><Link to="/inbox">Open the inbox</Link></Button>
      </div>
      <p className="mt-8 text-sm text-foreground/60">Curious what's underneath, and how well it does? <Link to="/about" className="underline underline-offset-2">How it works</Link>.</p>
    </div>
  )
}
