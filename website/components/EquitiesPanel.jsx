'use client'
import { useState } from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui/card'

const GROUP_LABELS = {
  us:         'United States',
  europe:     'Europe',
  asia:       'Asia',
  em:         'Emerging Markets',
  volatility: 'Volatility',
}

function fmtLevel(v) {
  if (v == null) return '—'
  if (v >= 10000) return v.toLocaleString('en-US', { maximumFractionDigits: 0 })
  if (v >= 1000)  return v.toLocaleString('en-US', { maximumFractionDigits: 1 })
  return v.toFixed(2)
}

function fmtPct(v) {
  if (v == null) return '—'
  return (v > 0 ? '+' : '') + v.toFixed(2) + '%'
}

function pctColor(v, isVol = false) {
  if (v == null || v === 0) return 'text-[#64748B]'
  if (isVol) return v > 0 ? 'text-[#EF4444]' : 'text-[#22C55E]'
  return v > 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'
}

export default function EquitiesPanel({ equities }) {
  const [collapsed, setCollapsed] = useState({})
  if (!equities) return null

  const toggle = k => setCollapsed(c => ({ ...c, [k]: !c[k] }))

  return (
    <Card className="bg-[#0F172A] border-[#1E293B] overflow-hidden">
      <CardHeader className="px-4 py-3 border-b border-[#1E293B] flex flex-row items-center justify-between space-y-0">
        <span className="font-sans text-[11px] font-semibold uppercase tracking-widest text-[#94A3B8]">Equities</span>
        <div className="flex gap-3 font-sans text-[10px] text-[#64748B] uppercase tracking-wider">
          <span className="w-20 text-right">Level</span>
          <span className="w-16 text-right">Δ</span>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {Object.entries(equities).map(([group, rows]) => {
          if (!rows?.length) return null
          const isVol = group === 'volatility'
          return (
            <div key={group}>
              <button
                onClick={() => toggle(group)}
                className="w-full flex items-center justify-between px-4 py-1.5 bg-[#1E293B]/50 hover:bg-[#1E293B] transition-colors border-b border-[#1E293B]"
              >
                <span className="font-sans text-[10px] uppercase tracking-widest text-[#64748B]">
                  {GROUP_LABELS[group] ?? group}
                </span>
                <span className="text-[#64748B] text-xs">{collapsed[group] ? '▸' : '▾'}</span>
              </button>
              {!collapsed[group] && rows.map((a, i) => (
                <div
                  key={a.key}
                  className={`flex items-center px-4 py-1.5 border-b border-[#1E293B] last:border-0 ${i % 2 === 1 ? 'bg-[#1E293B]/20' : ''}`}
                >
                  <span className="flex-1 font-sans text-xs text-[#CBD5E1]">{a.label}</span>
                  <span className="font-sans text-xs text-[#F8FAFC] w-20 text-right">{fmtLevel(a.close)}</span>
                  <span className={`font-sans text-xs w-16 text-right ${pctColor(a.change_pct, isVol)}`}>{fmtPct(a.change_pct)}</span>
                </div>
              ))}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
