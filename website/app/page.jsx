import { getLatestIssue, getAllIssues } from '../lib/content.js'
import Header           from '../components/Header.jsx'
import MarketSnapshot   from '../components/MarketSnapshot.jsx'
import ImplicationChain from '../components/ImplicationChain.jsx'
import Archive          from '../components/Archive.jsx'

function formatDate(d) {
  return new Date(d + 'T12:00:00Z').toLocaleDateString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  })
}

export default function Home() {
  const latest    = getLatestIssue()
  const allIssues = getAllIssues()

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-14">

        {latest ? (
          <section>
            {/* Date heading */}
            <div className="mb-7">
              <div className="text-[10px] uppercase tracking-widest text-primary-light mb-1">
                Latest Issue
              </div>
              <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
                {formatDate(latest.date)}
              </h1>
            </div>

            <div className="space-y-10">
              <MarketSnapshot  snapshot={latest.snapshot} />
              <ImplicationChain chain={latest.chain} />
            </div>
          </section>
        ) : (
          <div className="text-center py-24">
            <p className="text-subtle">No issues yet — run the pipeline.</p>
          </div>
        )}

        {allIssues.length > 1 && <Archive issues={allIssues} />}

        {/* About */}
        <section id="about" className="border-t border-border pt-10">
          <div className="max-w-2xl space-y-5 text-sm text-muted-foreground leading-relaxed">
            <div className="text-[10px] uppercase tracking-widest text-subtle mb-1">About</div>
            <p>
              Downstream traces cause-and-effect through financial markets. Not "oil up 3%" —
              but oil up → inflation expectations shift → Fed pauses → bonds sell off → EUR/USD drops.
              Every day, one chain.
            </p>
            <div className="border-l-2 border-primary pl-4">
              <p className="text-dimmed">
                Written by a master's student at Stockholm School of Economics who works at the Riksbank
                producing SWESTR daily. Background in fixed income, FX, rates, futures, and commodities.
              </p>
            </div>
          </div>
        </section>

      </main>

      <footer className="border-t border-border mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4">

          {/* Data source legend */}
          <div>
            <p className="text-[10px] uppercase tracking-widest text-subtle mb-2">Data sources</p>
            <div className="flex flex-wrap gap-x-5 gap-y-1">
              {[
                ['FRED', 'Federal Reserve (St. Louis)'],
                ['ECB',  'European Central Bank'],
                ['RIX',  'Riksbank (Sweden)'],
                ['BoE',  'Bank of England'],
                ['BBK',  'Deutsche Bundesbank'],
                ['MoF',  'Ministry of Finance (Japan)'],
                ['YF',   'Yahoo Finance / yfinance'],
                ['TD',   'Twelve Data'],
                ['AV',   'Alpha Vantage'],
              ].map(([abbr, full]) => (
                <span key={abbr} className="text-[11px] text-subtle">
                  <span className="font-mono text-muted-foreground">{abbr}</span>
                  <span className="text-subtle/60"> · {full}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Bottom line */}
          <div className="flex items-center justify-between pt-2 border-t border-border/50">
            <span className="text-xs text-subtle">Downstream</span>
            <span className="text-xs text-subtle">{latest?.date ?? ''}</span>
          </div>

        </div>
      </footer>
    </div>
  )
}
