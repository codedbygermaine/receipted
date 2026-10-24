import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export default function Landing() {
  return (
    <div className="mx-auto max-w-2xl py-6 sm:py-14">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Expense claims, checked against the receipt.</h1>
      <p className="mt-3 text-lg text-foreground/70">Hand in a receipt and a claim. You get a clear answer in about ten seconds, and every problem it finds points at the line on the receipt and the rule behind it.</p>
      <Button asChild size="lg" className="mt-8"><Link to="/claim">Try a claim</Link></Button>
      <div className="mt-12 border-t pt-8 sm:flex sm:items-start sm:justify-between sm:gap-8">
        <div>
          <h2 className="font-medium">Treasurer?</h2>
          <p className="mt-1 text-sm text-foreground/70">Claims the checker couldn't settle wait in an inbox, with the receipt and the reason side by side. Your decision writes the reply.</p>
        </div>
        <Button asChild variant="outline" className="mt-3 sm:mt-0 sm:shrink-0"><Link to="/inbox">Open the inbox</Link></Button>
      </div>
      <p className="mt-8 text-sm"><Link to="/about" className="text-foreground/70 underline underline-offset-2 hover:text-foreground">How it works</Link></p>
    </div>
  )
}
