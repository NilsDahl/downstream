'use client'
import { useState } from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui/card'
import { fxDollarStrengthened } from '../lib/utils.js'

const GROUP_LABELS = {
  majors:    'Majors',
  commodity: 'Commodity',
  em:        'Emerging Markets',
  cross:     'Cross Rates',
  index:     'Dollar Index',
}

function fmtLevel(v) { return v == null ? '—' : v.toFixed(4) }
function fmtPct(v) {
  if (v == null) return '—'
  return (v > 0 ? '+' : '') + v.toFixed(2) + '%'
}

function fxColor(key, pct) {
  if (pct == null) return 'text-[#64748B]'
  const isCross = !key.includes('usd') && !key.includes('dxy')
  if (isCross) return pct > 0 ? 'text-[#22C55E]' : pct < 0 ? 'text-[#EF4444]' : 'text-[#64748B]'
  const strong = fxDollarStrengthened(key, pct)
  if (strong === null) return 'text-[#64748B]'
  return strong ? 'text-[#EF4444]' : 'text-[#22C55E]'
}

export default function FXPanel({ fx }) {
  const [collapsed, setCollapsed] = useState({})
  if (!fx) return null

  const toggle = k => setCollapsed(c => ({ ...c, [k]: !c[k] }))

  return (
    <Card className="bg-[#0F172A] border-[#1E293B] overflow-hidden">
      <CardHeader className="px-4 py-3 border-b border-[#1E293B] flex flex-row items-center justify-between space-y-0">
        <span className="font-sans text-[11px] font-semibold uppercase tracking-widest text-[#94A3B8]">FX</span>
        <div className="flex gap-3 font-sans text-[10px] text-[#64748B] uppercase tracking-wider">
          <span className="w-20 text-right">Level</span>
          <span className="w-16 text-right">Δ</span>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {Object.entries(fx).map(([group, rows]) => {
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
                  <span className="font-sans text-xs text-[#F8FAFC] w-20 text-right">{fmtLevel(a.close)}</span>
                  <span className={`font-sans text-xs w-16 text-right ${fxColor(a.key, a.change_pct)}`}>{fmtPct(a.change_pct)}</span>
                </div>
              ))}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
