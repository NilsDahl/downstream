// ImplicationChain — the editorial heart of Downstream.
// Horizontal sequence of cards connected by arrows; vertical on mobile.

function Arrow() {
  return (
    <div className="flex-shrink-0 flex items-center justify-center w-6 md:w-8 text-amber">
      {/* Vertical on mobile, horizontal on desktop */}
      <svg
        className="hidden md:block"
        width="24" height="16" viewBox="0 0 24 16" fill="none"
        aria-hidden="true"
      >
        <path d="M0 8 H20 M14 2 L22 8 L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
      <svg
        className="md:hidden"
        width="16" height="24" viewBox="0 0 16 24" fill="none"
        aria-hidden="true"
      >
        <path d="M8 0 V20 M2 14 L8 22 L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </div>
  )
}

function DriverCard({ text }) {
  return (
    <div className="flex-shrink-0 w-64 md:w-72 rounded-lg border-2 border-amber bg-amber-light p-4">
      <div className="font-mono text-[10px] uppercase tracking-widest text-amber mb-2">
        The Driver
      </div>
      <p className="font-serif text-sm text-ink leading-snug">{text}</p>
    </div>
  )
}

function ChainNode({ label, body, index }) {
  return (
    <div className="flex-shrink-0 w-64 md:w-72 rounded-lg border border-border bg-white p-4 shadow-sm">
      <div className="font-mono text-[10px] uppercase tracking-widest text-ink-muted mb-1">
        Node {index + 1}
      </div>
      <div className="font-serif text-sm font-semibold text-ink mb-2 leading-snug">
        {label}
      </div>
      <p className="text-xs text-ink-muted leading-relaxed line-clamp-4">{body}</p>
    </div>
  )
}

function WatchNode({ text }) {
  // Parse numbered items if present
  const items = text
    .split(/\n\s*\d+\.\s+/)
    .map(s => s.trim())
    .filter(Boolean)

  return (
    <div className="flex-shrink-0 w-64 md:w-80 rounded-lg border-2 border-ink bg-ink p-4 shadow-sm">
      <div className="font-mono text-[10px] uppercase tracking-widest text-parchment/60 mb-2">
        What to Watch
      </div>
      {items.length > 1 ? (
        <ol className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="flex gap-2">
              <span className="font-mono text-[10px] text-amber mt-0.5 flex-shrink-0">{i + 1}.</span>
              <p className="text-xs text-parchment/90 leading-relaxed line-clamp-3">{item.replace(/^\*\*[^*]+\*\*\s*/, '')}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-xs text-parchment/90 leading-relaxed">{text}</p>
      )}
    </div>
  )
}

export default function ImplicationChain({ chain }) {
  if (!chain || (!chain.driver && chain.nodes.length === 0)) return null

  return (
    <section>
      <h2 className="font-mono text-xs uppercase tracking-widest text-ink-muted mb-4">
        Implication Chain
      </h2>

      {/* Horizontal scroll on desktop, vertical stack on mobile */}
      <div className="flex flex-col md:flex-row md:items-start md:overflow-x-auto md:pb-4 gap-0 md:gap-0">
        {chain.driver && (
          <>
            <DriverCard text={chain.driver} />
            {chain.nodes.length > 0 && <Arrow />}
          </>
        )}

        {chain.nodes.map((node, i) => (
          <div key={i} className="flex flex-col md:flex-row md:items-start">
            <ChainNode label={node.label} body={node.body} index={i} />
            {(i < chain.nodes.length - 1 || chain.watchText) && <Arrow />}
          </div>
        ))}

        {chain.watchText && <WatchNode text={chain.watchText} />}
      </div>
    </section>
  )
}
