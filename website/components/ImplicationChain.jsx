import { Card, CardContent } from '@/components/ui/card'
import ReactMarkdown from 'react-markdown'

function VerticalConnector() {
  return (
    <div className="flex flex-col items-center py-1">
      <div className="w-px h-4 bg-[#1D4ED8]/50" />
      <svg width="12" height="8" viewBox="0 0 12 8" className="text-[#1D4ED8]">
        <path d="M6 8 L0 0 L12 0 Z" fill="currentColor" />
      </svg>
    </div>
  )
}

function DriverCard({ text }) {
  return (
    <Card className="border-[#1D4ED8] bg-[#1E3A5F]/30 overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-1.5 h-1.5 rounded-full bg-[#3B82F6]" />
          <span className="font-sans text-[10px] uppercase tracking-widest text-[#3B82F6] font-semibold">
            The Driver
          </span>
        </div>
        <p className="text-[#F8FAFC] text-sm leading-relaxed">{text}</p>
      </CardContent>
    </Card>
  )
}

function ChainNode({ label, body, index }) {
  return (
    <Card className="border-[#1E293B] bg-[#0F172A] hover:border-[#334155] transition-colors overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-[#1E293B] border border-[#334155] flex items-center justify-center mt-0.5">
            <span className="font-sans text-[10px] text-[#64748B]">{index + 1}</span>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-[#F8FAFC] text-sm mb-2 leading-snug">{label}</h3>
            <div className="chain-prose text-sm text-[#94A3B8] leading-relaxed">
              <ReactMarkdown>{body}</ReactMarkdown>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function WatchCard({ text }) {
  return (
    <Card className="border-[#1D4ED8]/50 bg-[#020817] overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-1.5 h-1.5 rounded-full bg-[#1D4ED8]" />
          <span className="font-sans text-[10px] uppercase tracking-widest text-[#3B82F6] font-semibold">
            What to Watch
          </span>
        </div>
        <div className="chain-prose text-sm text-[#94A3B8] leading-relaxed">
          <ReactMarkdown>{text}</ReactMarkdown>
        </div>
      </CardContent>
    </Card>
  )
}

export default function ImplicationChain({ chain }) {
  if (!chain || (!chain.driver && chain.nodes.length === 0)) return null

  return (
    <section>
      <div className="flex items-center gap-4 mb-6">
        <span className="font-sans text-xl font-semibold text-white">
          Implication Chain
        </span>
        <div className="flex-1 h-px bg-[#1E293B]" />
      </div>

      <div className="w-full space-y-0">
        {chain.driver && (
          <>
            <DriverCard text={chain.driver} />
            {chain.nodes.length > 0 && <VerticalConnector />}
          </>
        )}

        {chain.nodes.map((node, i) => (
          <div key={i}>
            <ChainNode label={node.label} body={node.body} index={i} />
            {(i < chain.nodes.length - 1 || chain.watchText) && <VerticalConnector />}
          </div>
        ))}

        {chain.watchText && <WatchCard text={chain.watchText} />}
      </div>
    </section>
  )
}
