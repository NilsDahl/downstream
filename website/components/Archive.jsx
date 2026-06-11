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
      <Card className="h-full bg-[#0F172A] border-[#1E293B] hover:border-[#1D4ED8]/50 transition-all duration-150 overflow-hidden">
        <CardContent className="p-5 flex flex-col gap-3 h-full">
          <div className="font-sans text-[10px] text-[#64748B] uppercase tracking-wider">
            {formatDate(date)}
          </div>
          {driver && (
            <p className="text-sm text-[#CBD5E1] leading-snug line-clamp-3 flex-1 group-hover:text-white transition-colors">
              {driver}
            </p>
          )}
          {movers?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {movers.map((m, i) => (
                <Badge
                  key={i}
                  variant="outline"
                  className={`font-sans text-[10px] border px-2 py-0.5 ${
                    m.positive
                      ? 'text-[#22C55E] border-[#22C55E]/30 bg-[#22C55E]/5'
                      : 'text-[#EF4444] border-[#EF4444]/30 bg-[#EF4444]/5'
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
        <span className="font-sans text-[11px] uppercase tracking-widest text-[#64748B]">Archive</span>
        <div className="flex-1 h-px bg-[#1E293B]" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {archiveIssues.map(issue => (
          <IssueCard key={issue.date} date={issue.date} driver={issue.driver} movers={issue.movers} />
        ))}
      </div>
    </section>
  )
}
