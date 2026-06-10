'use client'
import { useState } from 'react'
import { fxDollarStrengthened } from '../lib/utils.js'

const GROUP_LABELS = {
  majors:    'Majors',
  commodity: 'Commodity',
  em:        'Emerging Markets',
  cross:     'Cross Rates',
  index:     'Dollar Index',
}

function fmtLevel(v) {
  if (v == null) return '—'
  return v.toFixed(4)
}

function fmtPct(v) {
  if (v == null) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

// Dollar-centric coloring: red = dollar stronger, green = dollar weaker
function fxColor(key, changePct) {
  if (changePct == null) return 'text-ink-muted'
  // For cross rates (no USD), use standard green/red
  const isCross = !key.includes('usd') && !key.includes('dxy')
  if (isCross) return changePct > 0 ? 'text-up' : changePct < 0 ? 'text-down' : 'text-ink-muted'

  const dollarStrengthened = fxDollarStrengthened(key, changePct)
  if (dollarStrengthened === null) return 'text-ink-muted'
  return dollarStrengthened ? 'text-down' : 'text-up'
}

export default function FXPanel({ fx }) {
  const [collapsed, setCollapsed] = useState({})
  if (!fx) return null

  const toggle = (key) => setCollapsed(c => ({ ...c, [key]: !c[key] }))

  return (
    <div className="bg-white rounded-lg shadow-sm border border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-ink">
          FX
        </h2>
        <div className="flex gap-4 font-mono text-[10px] text-ink-muted uppercase tracking-wider">
          <span className="w-20 text-right">Level</span>
          <span className="w-16 text-right">Δ</span>
        </div>
      </div>
      {Object.entries(fx).map(([group, rows]) => (
        <div key={group}>
          <button
            onClick={() => toggle(group)}
            className="w-full flex items-center justify-between px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-ink-muted bg-row-alt border-b border-border hover:bg-row-alt cursor-pointer"
          >
            <span>{GROUP_LABELS[group] ?? group}</span>
            <span>{collapsed[group] ? '▸' : '▾'}</span>
          </button>
          {!collapsed[group] && rows.map((asset, i) => (
            <div
              key={asset.key}
              className={`flex items-center px-3 py-1.5 border-b border-border last:border-0 ${i % 2 === 1 ? 'bg-row-alt/40' : ''}`}
            >
              <span className="flex-1 font-mono text-xs text-ink">{asset.label}</span>
              <span className="font-mono text-xs text-ink w-20 text-right">
                {fmtLevel(asset.close)}
              </span>
              <span className={`font-mono text-xs w-16 text-right ${fxColor(asset.key, asset.change_pct)}`}>
                {fmtPct(asset.change_pct)}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
