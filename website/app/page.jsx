import { getLatestIssue, getAllIssues } from '../lib/content.js'
import Header          from '../components/Header.jsx'
import MarketSnapshot  from '../components/MarketSnapshot.jsx'
import ImplicationChain from '../components/ImplicationChain.jsx'
import IssueBody       from '../components/IssueBody.jsx'
import Archive         from '../components/Archive.jsx'

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00Z')
  return d.toLocaleDateString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  })
}

export default function Home() {
  const latest = getLatestIssue()
  const allIssues = getAllIssues()

  return (
    <div className="min-h-screen">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-16">

        {/* Latest issue */}
        {latest ? (
          <section>
            <div className="mb-8">
              <div className="font-mono text-xs uppercase tracking-widest text-ink-muted mb-1">
                Latest Issue
              </div>
              <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink">
                {formatDate(latest.date)}
              </h1>
            </div>

            <div className="space-y-12">
              <MarketSnapshot  snapshot={latest.snapshot} />
              <ImplicationChain chain={latest.chain} />
              <IssueBody       content={latest.content} />
            </div>
          </section>
        ) : (
          <div className="text-center py-24">
            <p className="font-serif text-xl text-ink-muted">No issues yet.</p>
            <p className="font-mono text-xs text-ink-muted mt-2">
              Run the pipeline to generate your first draft.
            </p>
          </div>
        )}

        {/* Archive */}
        {allIssues.length > 1 && <Archive issues={allIssues} />}

        {/* About */}
        <section id="about" className="border-t border-border pt-12">
          <div className="max-w-2xl space-y-6">
            <h2 className="font-serif text-2xl font-bold text-ink">About Downstream</h2>
            <div className="space-y-4 text-sm text-ink leading-relaxed">
              <p>
                Downstream is a daily macro-finance brief built around a single idea:
                markets move in chains, not in isolation. When oil rises, it doesn't
                just mean oil is up — it means inflation expectations shift, central
                bank calculus changes, bond markets reprice, and currencies follow.
                Downstream traces that chain, every day.
              </p>
              <p>
                The brief is written for finance students and young professionals who
                want to understand macro but don't sit on a Bloomberg terminal.
                The goal is not to predict — it's to explain the mechanism behind
                the move.
              </p>
            </div>
            <div className="border-l-2 border-amber pl-4 space-y-2">
              <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">
                Author
              </p>
              <p className="text-sm text-ink leading-relaxed">
                Master's student at Stockholm School of Economics. Works at the
                Riksbank producing SWESTR daily. Background in fixed income, FX,
                rates, futures, and commodities.
              </p>
            </div>
            <div className="border-l-2 border-border pl-4 space-y-2">
              <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">
                Methodology
              </p>
              <p className="text-sm text-ink leading-relaxed">
                Daily market data is fetched at 09:30 Stockholm time from FRED,
                ECB, Riksbank, Bundesbank, Bank of England, and Japan MoF — covering
                yield curves across six economies, 30+ FX pairs, major equity
                indices, and the full commodity complex. A language model then
                identifies the primary driver and traces its implication chain.
                The author reviews and approves before publication.
              </p>
            </div>
          </div>
        </section>

      </main>

      <footer className="border-t border-border mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex items-center justify-between">
          <span className="font-serif text-sm text-ink-muted">Downstream</span>
          <span className="font-mono text-xs text-ink-muted">
            {latest?.date ?? ''}
          </span>
        </div>
      </footer>
    </div>
  )
}
