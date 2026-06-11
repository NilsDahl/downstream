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
    <div className="min-h-screen bg-[#020817]">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-14">

        {latest ? (
          <section>
            {/* Date heading */}
            <div className="mb-7">
              <div className="font-sans text-[10px] uppercase tracking-widest text-[#3B82F6] mb-1">
                Latest Issue
              </div>
              <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight">
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
            <p className="font-sans text-[#64748B]">No issues yet — run the pipeline.</p>
          </div>
        )}

        {allIssues.length > 1 && <Archive issues={allIssues} />}

        {/* About */}
        <section id="about" className="border-t border-[#1E293B] pt-10">
          <div className="max-w-2xl space-y-5 text-sm text-[#94A3B8] leading-relaxed">
            <div className="font-sans text-[10px] uppercase tracking-widest text-[#64748B] mb-1">About</div>
            <p>
              Downstream traces cause-and-effect through financial markets. Not "oil up 3%" —
              but oil up → inflation expectations shift → Fed pauses → bonds sell off → EUR/USD drops.
              Every day, one chain.
            </p>
            <div className="border-l-2 border-[#1D4ED8] pl-4">
              <p className="text-[#CBD5E1]">
                Written by a master's student at Stockholm School of Economics who works at the Riksbank
                producing SWESTR daily. Background in fixed income, FX, rates, futures, and commodities.
              </p>
            </div>
          </div>
        </section>

      </main>

      <footer className="border-t border-[#1E293B] mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex items-center justify-between">
          <span className="font-sans text-xs text-[#64748B]">Downstream</span>
          <span className="font-sans text-xs text-[#64748B]">{latest?.date ?? ''}</span>
        </div>
      </footer>
    </div>
  )
}
