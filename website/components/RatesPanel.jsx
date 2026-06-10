'use client'
import { useState } from 'react'

const ECONOMY_LABELS = {
  us:       'United States',
  eurozone: 'Eurozone',
  germany:  'Germany',
  sweden:   'Sweden',
  uk:       'United Kingdom',
  japan:    'Japan',
}

function fmtLevel(level) {
  if (level == null) return '—'
  return level.toFixed(2) + '%'
}

function fmtBps(bps) {
  if (bps == null) return '—'
  const sign = bps > 0 ? '+' : ''
  return `${sign}${bps.toFixed(1)}bp`
}

// Yields up = tightening = red. Yields down = easing = green.
function bpsColor(bps) {
  if (bps == null) return 'text-ink-muted'
  if (bps > 0)  return 'text-down'
  if (bps < 0)  return 'text-up'
  return 'text-ink-muted'
}

function EconomyGroup({ label, rows }) {
  if (!rows || rows.length === 0) return null
  return (
    <div>
      <div className="px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-ink-muted bg-row-alt border-b border-border">
        {label}
      </div>
      {rows.map((asset, i) => (
        <div
          key={asset.key}
          className={`flex items-center px-3 py-1.5 text-sm border-b border-border last:border-0 ${i % 2 === 1 ? 'bg-row-alt/40' : ''}`}
        >
          <span className="flex-1 font-mono text-xs text-ink">{asset.label}</span>
          <span className="font-mono text-xs text-ink w-16 text-right">
            {fmtLevel(asset.level)}
          </span>
          <span className={`font-mono text-xs w-16 text-right ${bpsColor(asset.change_bps)}`}>
            {fmtBps(asset.change_bps)}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function RatesPanel({ rates }) {
  const [collapsed, setCollapsed] = useState({})

  if (!rates) return null

  const toggle = (key) => setCollapsed(c => ({ ...c, [key]: !c[key] }))

  return (
    <div className="bg-white rounded-lg shadow-sm border border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-ink">
          Yield Curves
        </h2>
        <div className="flex gap-4 font-mono text-[10px] text-ink-muted uppercase tracking-wider">
          <span className="w-16 text-right">Level</span>
          <span className="w-16 text-right">Δ (bp)</span>
        </div>
      </div>
      {Object.entries(rates).map(([econ, rows]) => (
        <div key={econ}>
          <button
            onClick={() => toggle(econ)}
            className="w-full flex items-center justify-between px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-ink-muted bg-row-alt border-b border-border hover:bg-row-alt cursor-pointer"
          >
            <span>{ECONOMY_LABELS[econ] ?? econ}</span>
            <span>{collapsed[econ] ? '▸' : '▾'}</span>
          </button>
          {!collapsed[econ] && rows.map((asset, i) => (
            <div
              key={asset.key}
              className={`flex items-center px-3 py-1.5 text-sm border-b border-border last:border-0 ${i % 2 === 1 ? 'bg-row-alt/40' : ''}`}
            >
              <span className="flex-1 font-mono text-xs text-ink">{asset.label}</span>
              <span className="font-mono text-xs text-ink w-16 text-right">
                {fmtLevel(asset.level)}
              </span>
              <span className={`font-mono text-xs w-16 text-right ${bpsColor(asset.change_bps)}`}>
                {fmtBps(asset.change_bps)}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
