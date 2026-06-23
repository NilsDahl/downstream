'use client'
import { useState } from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui/card'
import { fxDollarStrengthened } from '../lib/utils.js'
import SourceTag from './SourceTag.jsx'

const GROUP_LABELS = {
  majors:    'Majors',
  commodity: 'Commodity',
  em:        'Emerging Markets',
  cross:     'Cross Rates',
  index:     'Dollar Index',
}

const fmtLevel = v => v == null ? '—' : v.toFixed(4)
const fmtPct   = v => v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(2) + '%'

function fxColor(key, pct) {
  if (pct == null) return 'text-subtle'
  const isCross = !key.includes('usd') && !key.includes('dxy')
  if (isCross) return pct > 0 ? 'text-up' : pct < 0 ? 'text-down' : 'text-subtle'
  const strong = fxDollarStrengthened(key, pct)
  if (strong === null) return 'text-subtle'
  return strong ? 'text-down' : 'text-up'
}

export default function FXPanel({ fx }) {
  const [collapsed, setCollapsed] = useState({})
  if (!fx) return null
  const toggle = k => setCollapsed(c => ({ ...c, [k]: !c[k] }))

  return (
    <Card className="bg-card border-border overflow-hidden">
      <CardHeader className="px-4 py-3 border-b border-border flex flex-row items-center justify-between space-y-0">
        <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">FX</span>
        <div className="flex gap-3 text-[10px] text-subtle uppercase tracking-wider">
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
                  className={`flex items-center px-4 py-1.5 border-b border-border last:border-0 ${i % 2 === 1 ? 'bg-muted/20' : ''} ${a.missing ? 'opacity-40' : ''}`}
                >
                  <span className="flex-1 text-xs text-dimmed flex items-center">
                    {a.label}
                    <SourceTag source={a.source} missing={a.missing} />
                  </span>
                  <span className="text-xs text-foreground w-20 text-right">{fmtLevel(a.close)}</span>
                  <span className={`text-xs w-16 text-right ${fxColor(a.key, a.change_pct)}`}>{fmtPct(a.change_pct)}</span>
                </div>
              ))}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
