export default function Header() {
  return (
    <header className="border-b border-border bg-parchment sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-baseline gap-4">
        <a href="/" className="font-serif text-2xl font-bold tracking-tight text-ink">
          Downstream
        </a>
        <span className="font-mono text-xs text-ink-muted uppercase tracking-widest">
          Follow the chain.
        </span>
      </div>
    </header>
  )
}
