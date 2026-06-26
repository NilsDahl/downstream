import { Card, CardContent } from '@/components/ui/card'
import ReactMarkdown from 'react-markdown'

function formatTime(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })
  } catch {
    return ''
  }
}

export default function NewsTab({ newsSummary, newsItems }) {
  if (!newsSummary && (!newsItems || newsItems.length === 0)) {
    return (
      <p className="text-sm text-subtle py-6">No news summary available for this date.</p>
    )
  }

  return (
    <div className="space-y-6">
      {newsSummary && (
        <Card className="border-border bg-card">
          <CardContent className="p-6">
            <div className="news-prose text-sm text-muted-foreground leading-relaxed">
              <ReactMarkdown>{newsSummary}</ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      )}

      {newsItems && newsItems.length > 0 && (
        <Card className="border-border bg-card">
          <CardContent className="p-6">
            <p className="text-[10px] uppercase tracking-widest text-subtle mb-4">Sources</p>
            <ul className="space-y-3">
              {newsItems.map((item, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="text-[11px] text-subtle shrink-0 w-28 truncate pt-px">
                    {item.source}
                    {item.publishedAt && (
                      <span className="text-subtle/60 ml-1">{formatTime(item.publishedAt)}</span>
                    )}
                  </span>
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors leading-snug"
                  >
                    {item.headline}
                  </a>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
