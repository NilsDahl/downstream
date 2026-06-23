import { Card, CardContent } from '@/components/ui/card'
import ReactMarkdown from 'react-markdown'

export default function NewsTab({ newsSummary }) {
  if (!newsSummary) {
    return (
      <p className="text-sm text-subtle py-6">No news summary available for this date.</p>
    )
  }

  return (
    <Card className="border-border bg-card">
      <CardContent className="p-6">
        <div className="news-prose text-sm text-muted-foreground leading-relaxed">
          <ReactMarkdown>{newsSummary}</ReactMarkdown>
        </div>
      </CardContent>
    </Card>
  )
}
