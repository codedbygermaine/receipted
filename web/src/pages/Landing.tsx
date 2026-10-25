import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export default function Landing() {
  return (
    <div className="mx-auto max-w-2xl py-6 sm:py-14">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">An AI agent that checks expense claims.</h1>
      <p className="mt-4 text-lg text-foreground/70">Upload a receipt and enter the amount you’re claiming. Receipted checks whether the amount matches the receipt and whether the purchase is covered by the expense policy. It explains any problems and tells you whether the claim is approved, needs review or is rejected.</p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button asChild size="lg"><Link to="/claim">Try a sample claim</Link></Button>
        <Button asChild variant="outline" size="lg"><Link to="/inbox">Review a claim</Link></Button>
      </div>
    </div>
  )
}
