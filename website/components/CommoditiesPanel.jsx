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

const fmtPct  = v => v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(2) + '%'
const pctColor = v => v == null || v === 0 ? 'text-subtle' : v > 0 ? 'text-up' : 'text-down'

export default function CommoditiesPanel({ commodities }) {
  const [collapsed, setCollapsed] = useState({})
  if (!commodities) return null
  const toggle = k => setCollapsed(c => ({ ...c, [k]: !c[k] }))

  return (
    <Card className="bg-card border-border overflow-hidden">
      <CardHeader className="px-4 py-3 border-b border-border flex flex-row items-center justify-between space-y-0">
        <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Commodities</span>
        <div className="flex gap-3 text-[10px] text-subtle uppercase tracking-wider">
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
                  <span className="text-xs text-foreground w-24 text-right">{fmtPrice(a.close, a.unit)}</span>
                  <span className={`text-xs w-16 text-right ${pctColor(a.change_pct)}`}>{fmtPct(a.change_pct)}</span>
                </div>
              ))}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
