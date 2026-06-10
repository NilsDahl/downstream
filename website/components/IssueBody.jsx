'use client'
import ReactMarkdown from 'react-markdown'
import remarkGfm    from 'remark-gfm'

export default function IssueBody({ content }) {
  if (!content) return null

  // Strip frontmatter-adjacent title and the chain section; keep only prose
  // We render the full content here so the reader gets the complete analysis
  const cleaned = content
    .replace(/^#\s+.+\n/, '')     // remove h1 title
    .trim()

  return (
    <section>
      <h2 className="font-mono text-xs uppercase tracking-widest text-ink-muted mb-4">
        Full Analysis
      </h2>
      <div className="issue-prose max-w-prose text-sm text-ink leading-relaxed">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {cleaned}
        </ReactMarkdown>
      </div>
    </section>
  )
}
