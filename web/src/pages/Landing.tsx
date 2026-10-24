import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export default function Landing() {
  return (
    <div className="mx-auto max-w-2xl py-6 sm:py-14">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Receipted checks expense claims against the receipt.</h1>
      <p className="mt-4 text-lg text-foreground/70">Members of a club buy things for the club and claim the money back. The treasurer has to check each claim: is there a receipt, does the amount match it, do the club's rules allow it. Receipted does that check in seconds and shows its reasons.</p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button asChild size="lg"><Link to="/claim">Try it as a member</Link></Button>
        <Button asChild variant="outline" size="lg"><Link to="/inbox">Open the treasurer's inbox</Link></Button>
      </div>
      <p className="mt-6 text-sm text-foreground/60">Pick one of six receipts, see what the checker says, then decide the held claims as the treasurer.</p>
      <p className="mt-8 text-sm"><Link to="/about" className="text-foreground/70 underline underline-offset-2 hover:text-foreground">How it works</Link></p>
    </div>
  )
}
