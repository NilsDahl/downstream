import { getAllDates, getIssue } from '../../../lib/content.js'
import Header           from '../../../components/Header.jsx'
import MarketSnapshot   from '../../../components/MarketSnapshot.jsx'
import ImplicationChain from '../../../components/ImplicationChain.jsx'
import Link             from 'next/link'

export async function generateStaticParams() {
  return getAllDates().map(date => ({ date }))
}

export async function generateMetadata({ params }) {
  const { date } = await params
  return { title: `Downstream — ${date}` }
}

function formatDate(d) {
  return new Date(d + 'T12:00:00Z').toLocaleDateString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  })
}

export default async function IssuePage({ params }) {
  const { date } = await params
  const issue = getIssue(date)

  if (!issue) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="max-w-7xl mx-auto px-4 py-20 text-center">
          <p className="text-subtle">Issue not found.</p>
          <Link href="/" className="text-xs text-primary-light mt-4 inline-block hover:underline">
            ← Back
          </Link>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
        <div>
          <Link href="/" className="text-[10px] text-subtle hover:text-primary-light transition-colors uppercase tracking-wider">
            ← All issues
          </Link>
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight mt-3">
            {formatDate(date)}
          </h1>
        </div>

        <MarketSnapshot   snapshot={issue.snapshot} />
        <ImplicationChain chain={issue.chain} />
      </main>

      <footer className="border-t border-border mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex items-center justify-between">
          <Link href="/" className="text-xs text-subtle hover:text-primary-light transition-colors">
            Downstream
          </Link>
          <span className="text-xs text-subtle">{date}</span>
        </div>
      </footer>
    </div>
  )
}
