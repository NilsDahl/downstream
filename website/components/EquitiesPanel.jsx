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

const fmtPct  = v => v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(2) + '%'

function pctColor(v, isVol = false) {
  if (v == null || v === 0) return 'text-subtle'
  if (isVol) return v > 0 ? 'text-down' : 'text-up'
  return v > 0 ? 'text-up' : 'text-down'
}

export default function EquitiesPanel({ equities }) {
  const [collapsed, setCollapsed] = useState({})
  if (!equities) return null
  const toggle = k => setCollapsed(c => ({ ...c, [k]: !c[k] }))

  return (
    <Card className="bg-card border-border overflow-hidden">
      <CardHeader className="px-4 py-3 border-b border-border flex flex-row items-center justify-between space-y-0">
        <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Equities</span>
        <div className="flex gap-3 text-[10px] text-subtle uppercase tracking-wider">
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
                className="w-full flex items-center justify-between px-4 py-1.5 bg-muted/50 hover:bg-muted transition-colors border-b border-border"
              >
                <span className="text-[10px] uppercase tracking-widest text-subtle">
                  {GROUP_LABELS[group] ?? group}
                </span>
                <span className="text-subtle text-xs">{collapsed[group] ? '▸' : '▾'}</span>
              </button>
              {!collapsed[group] && rows.map((a, i) => (
                <div
                  key={a.key}
                  className={`flex items-center px-4 py-1.5 border-b border-border last:border-0 ${i % 2 === 1 ? 'bg-muted/20' : ''}`}
                >
                  <span className="flex-1 text-xs text-dimmed">{a.label}</span>
                  <span className="text-xs text-foreground w-20 text-right">{fmtLevel(a.close)}</span>
                  <span className={`text-xs w-16 text-right ${pctColor(a.change_pct, isVol)}`}>{fmtPct(a.change_pct)}</span>
                </div>
              ))}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
