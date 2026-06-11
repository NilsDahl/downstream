'use client'
import { useState } from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui/card'

const ECONOMY_LABELS = {
  us:       'United States',
  eurozone: 'Eurozone',
  germany:  'Germany',
  sweden:   'Sweden',
  uk:       'United Kingdom',
  japan:    'Japan',
}

function fmtLevel(v) {
  return v == null ? '—' : v.toFixed(2) + '%'
}

function fmtBps(v) {
  if (v == null) return '—'
  return (v > 0 ? '+' : '') + v.toFixed(1) + 'bp'
}

// Yields up = tightening = red. Yields down = easing = green.
function bpsColor(v) {
  if (v == null || v === 0) return 'text-[#64748B]'
  return v > 0 ? 'text-[#EF4444]' : 'text-[#22C55E]'
}

export default function RatesPanel({ rates }) {
  const [collapsed, setCollapsed] = useState({})
  if (!rates) return null

  const toggle = k => setCollapsed(c => ({ ...c, [k]: !c[k] }))

  return (
    <Card className="bg-[#0F172A] border-[#1E293B] overflow-hidden">
      <CardHeader className="px-4 py-3 border-b border-[#1E293B] flex flex-row items-center justify-between space-y-0">
        <span className="font-mono text-[11px] font-semibold uppercase tracking-widest text-[#94A3B8]">
          Yield Curves
        </span>
        <div className="flex gap-3 font-mono text-[10px] text-[#64748B] uppercase tracking-wider">
          <span className="w-14 text-right">Level</span>
          <span className="w-14 text-right">Δ bp</span>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {Object.entries(rates).map(([econ, rows]) => {
          if (!rows?.length) return null
          return (
            <div key={econ}>
              <button
                onClick={() => toggle(econ)}
                className="w-full flex items-center justify-between px-4 py-1.5 text-left bg-[#1E293B]/50 hover:bg-[#1E293B] transition-colors border-b border-[#1E293B]"
              >
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#64748B]">
                  {ECONOMY_LABELS[econ] ?? econ}
                </span>
                <span className="text-[#64748B] text-xs">{collapsed[econ] ? '▸' : '▾'}</span>
              </button>
              {!collapsed[econ] && rows.map((a, i) => (
                <div
                  key={a.key}
                  className={`flex items-center px-4 py-1.5 border-b border-[#1E293B] last:border-0 ${i % 2 === 1 ? 'bg-[#1E293B]/20' : ''}`}
                >
                  <span className="flex-1 font-mono text-xs text-[#CBD5E1]">{a.label}</span>
                  <span className="font-mono text-xs text-[#F8FAFC] w-14 text-right">{fmtLevel(a.level)}</span>
                  <span className={`font-mono text-xs w-14 text-right ${bpsColor(a.change_bps)}`}>{fmtBps(a.change_bps)}</span>
                </div>
              ))}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
