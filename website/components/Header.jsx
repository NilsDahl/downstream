import Link from 'next/link'
import { ThemeToggle } from './ThemeToggle'

export default function Header() {
  return (
    <header className="border-b border-border bg-card">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="flex items-center justify-between gap-4">

          <Link href="/" className="group flex items-center gap-4">
            {/* Chain logo: 3 nodes connected by downward arrows */}
            <svg
              viewBox="0 0 16 54"
              className="h-[50px] sm:h-[56px] w-auto flex-shrink-0 transition-opacity duration-200 group-hover:opacity-80"
              fill="none"
              aria-hidden="true"
            >
              <circle cx="8" cy="5" r="4" fill="var(--primary)" />
              <line x1="8" y1="10" x2="8" y2="17" stroke="var(--primary)" strokeWidth="1.5" />
              <path d="M4 17 L8 23 L12 17 Z" fill="var(--primary)" />

              <circle cx="8" cy="27" r="4" fill="var(--primary-light)" />
              <line x1="8" y1="32" x2="8" y2="39" stroke="var(--primary-light)" strokeWidth="1.5" />
              <path d="M4 39 L8 45 L12 39 Z" fill="var(--primary-light)" />

              <circle cx="8" cy="49" r="4" fill="var(--primary-light)" fillOpacity="0.4" />
            </svg>

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
