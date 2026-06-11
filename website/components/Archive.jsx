import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

function formatDate(d) {
  return new Date(d + 'T12:00:00Z').toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
  })
}

function IssueCard({ date, driver, movers }) {
  return (
    <Link href={`/issue/${date}`} className="block group">
      <Card className="h-full bg-card border-border hover:border-primary/50 transition-all duration-150 overflow-hidden">
        <CardContent className="p-5 flex flex-col gap-3 h-full">
          <div className="text-[10px] text-subtle uppercase tracking-wider">
            {formatDate(date)}
          </div>
          {driver && (
            <p className="text-sm text-dimmed leading-snug line-clamp-3 flex-1 group-hover:text-foreground transition-colors">
              {driver}
            </p>
          )}
          {movers?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {movers.map((m, i) => (
                <Badge
                  key={i}
                  variant="outline"
                  className={`text-[10px] border px-2 py-0.5 ${
                    m.positive
                      ? 'text-up border-up/30 bg-up/5'
                      : 'text-down border-down/30 bg-down/5'
                  }`}
                >
                  {m.label} {m.val}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  )
}

export default function Archive({ issues }) {
  const archiveIssues = issues?.slice(1)
  if (!archiveIssues?.length) return null

  return (
    <section id="archive">
      <div className="flex items-center gap-3 mb-5">
        <span className="text-[11px] uppercase tracking-widest text-subtle">Archive</span>
        <div className="flex-1 h-px bg-border" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {archiveIssues.map(issue => (
          <IssueCard key={issue.date} date={issue.date} driver={issue.driver} movers={issue.movers} />
        ))}
      </div>
    </section>
  )
}
