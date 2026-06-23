'use client'
import { useState } from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui/card'
import SourceTag from './SourceTag.jsx'

const ECONOMY_LABELS = {
  us:       'United States',
  eurozone: 'Eurozone',
  germany:  'Germany',
  sweden:   'Sweden',
  uk:       'United Kingdom',
  japan:    'Japan',
}

const fmtLevel = v => v == null ? '—' : v.toFixed(2) + '%'
const fmtBps   = v => v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(1) + 'bp'

// Yields up = tightening = red. Yields down = easing = green.
const bpsColor = v => {
  if (v == null || v === 0) return 'text-subtle'
  return v > 0 ? 'text-down' : 'text-up'
}

export default function RatesPanel({ rates }) {
  const [collapsed, setCollapsed] = useState({})
  if (!rates) return null
  const toggle = k => setCollapsed(c => ({ ...c, [k]: !c[k] }))

  return (
    <Card className="bg-card border-border overflow-hidden">
      <CardHeader className="px-4 py-3 border-b border-border flex flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
            Yield Curves
          </span>
          <span className="text-[9px] font-mono text-muted-foreground/50 border border-border rounded px-1 py-px">T−1</span>
        </div>
        <div className="flex gap-3 text-[10px] text-subtle uppercase tracking-wider">
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
                className="w-full flex items-center justify-between px-4 py-1.5 text-left bg-muted/50 hover:bg-muted transition-colors border-b border-border"
              >
                <span className="text-[10px] uppercase tracking-widest text-subtle">
                  {ECONOMY_LABELS[econ] ?? econ}
                </span>
                <span className="text-subtle text-xs">{collapsed[econ] ? '▸' : '▾'}</span>
              </button>
              {!collapsed[econ] && rows.map((a, i) => (
                <div
                  key={a.key}
                  className={`flex items-center px-4 py-1.5 border-b border-border last:border-0 ${i % 2 === 1 ? 'bg-muted/20' : ''} ${a.missing ? 'opacity-40' : ''}`}
                >
                  <span className="flex-1 text-xs text-dimmed flex items-center">
                    {a.label}
                    <SourceTag source={a.source} missing={a.missing} />
                  </span>
                  <span className="text-xs text-foreground w-14 text-right">{fmtLevel(a.level)}</span>
                  <span className={`text-xs w-14 text-right ${bpsColor(a.change_bps)}`}>{fmtBps(a.change_bps)}</span>
                </div>
              ))}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
