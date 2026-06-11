import Link from 'next/link'
import { ThemeToggle } from './ThemeToggle'

export default function Header() {
  return (
    <header className="border-b border-border bg-card">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="flex items-center justify-between gap-4">

          <Link href="/" className="group flex items-center gap-4">
            <div className="flex flex-col gap-1">
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-primary" />
                <div className="w-2 h-2 rounded-full bg-primary-light" />
              </div>
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-primary-light" />
                <div className="w-2 h-2 rounded-full bg-primary-light/50" />
              </div>
            </div>

            <div>
              <div className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight leading-none group-hover:text-primary-light transition-colors duration-200">
                Downstream
              </div>
              <div className="text-xs text-primary-light tracking-widest uppercase mt-1">
                Follow the chain.
              </div>
            </div>
          </Link>

          <ThemeToggle />

          <div className="text-right hidden sm:block">
            <div className="text-[11px] text-subtle uppercase tracking-widest">
              Daily macro implication chains
            </div>
            <div className="text-[11px] text-subtle/60 mt-0.5">
              Rates · FX · Equities · Commodities
            </div>
          </div>

        </div>
      </div>
    </header>
  )
}
