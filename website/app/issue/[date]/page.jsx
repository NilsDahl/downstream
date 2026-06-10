import { getAllDates, getIssue } from '../../../lib/content.js'
import Header           from '../../../components/Header.jsx'
import MarketSnapshot   from '../../../components/MarketSnapshot.jsx'
import ImplicationChain from '../../../components/ImplicationChain.jsx'
import IssueBody        from '../../../components/IssueBody.jsx'
import Link             from 'next/link'

export async function generateStaticParams() {
  return getAllDates().map(date => ({ date }))
}

export async function generateMetadata({ params }) {
  const { date } = await params
  return {
    title: `Downstream — ${date}`,
  }
}

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00Z')
  return d.toLocaleDateString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  })
}

export default async function IssuePage({ params }) {
  const { date } = await params
  const issue = getIssue(date)

  if (!issue) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
          <p className="font-serif text-xl text-ink-muted">Issue not found.</p>
          <Link href="/" className="font-mono text-xs text-amber mt-4 inline-block hover:underline">
            ← Back to latest
          </Link>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
        <div>
          <Link href="/" className="font-mono text-xs text-ink-muted hover:text-amber transition-colors">
            ← All issues
          </Link>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold text-ink mt-3">
            {formatDate(date)}
          </h1>
        </div>

        <MarketSnapshot   snapshot={issue.snapshot} />
        <ImplicationChain chain={issue.chain} />
        <IssueBody        content={issue.content} />
      </main>

      <footer className="border-t border-border mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex items-center justify-between">
          <Link href="/" className="font-serif text-sm text-ink-muted hover:text-amber transition-colors">
            Downstream
          </Link>
          <span className="font-mono text-xs text-ink-muted">{date}</span>
        </div>
      </footer>
    </div>
  )
}
