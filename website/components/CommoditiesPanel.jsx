'use client'
import { useState } from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui/card'

const GROUP_LABELS = {
  energy:            'Energy',
  precious_metals:   'Precious Metals',
  industrial_metals: 'Industrial Metals',
  agriculture:       'Agriculture',
  other:             'Other',
}

function fmtPrice(close, unit) {
  if (close == null) return '—'
  if (unit?.startsWith('¢')) return `${close.toFixed(0)}${unit}`
  if (!unit) return close.toFixed(3)
  if (close >= 1000) return `$${Math.round(close).toLocaleString('en-US')}${unit}`
  if (close >= 10)   return `$${close.toFixed(2)}${unit}`
  return `$${close.toFixed(3)}${unit}`
}

function fmtPct(v) {
  if (v == null) return '—'
  return (v > 0 ? '+' : '') + v.toFixed(2) + '%'
}

function pctColor(v) {
  if (v == null || v === 0) return 'text-[#64748B]'
  return v > 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'
}

export default function CommoditiesPanel({ commodities }) {
  const [collapsed, setCollapsed] = useState({})
  if (!commodities) return null

  const toggle = k => setCollapsed(c => ({ ...c, [k]: !c[k] }))

  return (
    <Card className="bg-[#0F172A] border-[#1E293B] overflow-hidden">
      <CardHeader className="px-4 py-3 border-b border-[#1E293B] flex flex-row items-center justify-between space-y-0">
        <span className="font-sans text-[11px] font-semibold uppercase tracking-widest text-[#94A3B8]">Commodities</span>
        <div className="flex gap-3 font-sans text-[10px] text-[#64748B] uppercase tracking-wider">
          <span className="w-24 text-right">Price</span>
          <span className="w-16 text-right">Δ</span>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {Object.entries(commodities).map(([group, rows]) => {
          if (!rows?.length) return null
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
                  <span className="font-sans text-xs text-[#F8FAFC] w-24 text-right">{fmtPrice(a.close, a.unit)}</span>
                  <span className={`font-sans text-xs w-16 text-right ${pctColor(a.change_pct)}`}>{fmtPct(a.change_pct)}</span>
                </div>
              ))}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
