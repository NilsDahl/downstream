import Link from 'next/link'

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00Z')
  return d.toLocaleDateString('en-GB', {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  })
}

function MoverTag({ label, val, positive }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[10px] border ${
      positive
        ? 'text-up border-up/30 bg-up/5'
        : 'text-down border-down/30 bg-down/5'
    }`}>
      {label} <span className="font-semibold">{val}</span>
    </span>
  )
}

function IssueCard({ date, driver, movers }) {
  return (
    <Link href={`/issue/${date}`} className="block group">
      <article className="bg-white border border-border rounded-lg p-5 shadow-sm hover:shadow-md hover:border-amber/40 transition-all duration-150 h-full flex flex-col gap-3">
        <div className="font-mono text-xs text-ink-muted uppercase tracking-wider">
          {formatDate(date)}
        </div>
        {driver && (
          <p className="font-serif text-sm text-ink leading-snug line-clamp-3 flex-1 group-hover:text-amber transition-colors">
            {driver}
          </p>
        )}
        {movers && movers.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {movers.map((m, i) => (
              <MoverTag key={i} label={m.label} val={m.val} positive={m.positive} />
            ))}
          </div>
        )}
      </article>
    </Link>
  )
}

export default function Archive({ issues }) {
  if (!issues || issues.length === 0) return null

  // Exclude the most recent issue (it's shown as the latest)
  const archiveIssues = issues.slice(1)
  if (archiveIssues.length === 0) return null

  return (
    <section id="archive">
      <h2 className="font-mono text-xs uppercase tracking-widest text-ink-muted mb-4">
        Archive
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {archiveIssues.map(issue => (
          <IssueCard
            key={issue.date}
            date={issue.date}
            driver={issue.driver}
            movers={issue.movers}
          />
        ))}
      </div>
    </section>
  )
}
