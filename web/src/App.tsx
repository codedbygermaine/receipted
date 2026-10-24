import { useEffect } from "react"
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import Landing from "@/pages/Landing"
import Claim from "@/pages/Claim"
import Verdict from "@/pages/Verdict"
import Inbox from "@/pages/Inbox"
import About from "@/pages/About"

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

const navClass = ({ isActive }: { isActive: boolean }) =>
  `whitespace-nowrap rounded-full px-2.5 py-1.5 sm:px-3 ${isActive ? "bg-muted font-medium" : "text-foreground/70 hover:text-foreground"}`

export default function App() {
  return (
    <div className="min-h-dvh flex flex-col bg-background text-foreground">
      <ScrollToTop />
      <header className="sticky top-0 z-20 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3 sm:px-6">
          <Link to="/" className="flex shrink-0 items-center gap-2 font-semibold tracking-tight">
            <span className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground text-sm font-bold">R</span>
            <span>Receipted</span>
          </Link>
          <nav className="ml-auto flex items-center gap-0.5 text-sm">
            <NavLink to="/claim" className={navClass}><span className="sm:hidden">Members</span><span className="hidden sm:inline">For members</span></NavLink>
            <NavLink to="/inbox" className={navClass}><span className="sm:hidden">Treasurers</span><span className="hidden sm:inline">For treasurers</span></NavLink>
            <NavLink to="/about" className={navClass}><span className="sm:hidden">About</span><span className="hidden sm:inline">How it works</span></NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/claim" element={<Claim />} />
          <Route path="/claim/:jobId" element={<Verdict />} />
          <Route path="/inbox" element={<Inbox />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<Landing />} />
        </Routes>
      </main>
      <footer className="mx-auto w-full max-w-5xl px-4 py-6 text-xs text-foreground/60 sm:px-6">
        A project by Germaine
      </footer>
      <Toaster richColors position="bottom-center" />
    </div>
  )
}
