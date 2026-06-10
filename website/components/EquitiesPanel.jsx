'use client'
import { useState } from 'react'

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
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

function pctColor(v, isVol = false) {
  if (v == null) return 'text-ink-muted'
  // Volatility: rising VIX = bad (red), falling = good (green) — opposite of equities
  if (isVol) return v > 0 ? 'text-down' : v < 0 ? 'text-up' : 'text-ink-muted'
  return v > 0 ? 'text-up' : v < 0 ? 'text-down' : 'text-ink-muted'
}

export default function EquitiesPanel({ equities }) {
  const [collapsed, setCollapsed] = useState({})
  if (!equities) return null

  const toggle = (key) => setCollapsed(c => ({ ...c, [key]: !c[key] }))

  return (
    <div className="bg-white rounded-lg shadow-sm border border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-ink">
          Equities
        </h2>
        <div className="flex gap-4 font-mono text-[10px] text-ink-muted uppercase tracking-wider">
          <span className="w-20 text-right">Level</span>
          <span className="w-16 text-right">Δ</span>
        </div>
      </div>
      {Object.entries(equities).map(([group, rows]) => {
        if (!rows || rows.length === 0) return null
        const isVol = group === 'volatility'
        return (
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
                <span className={`font-mono text-xs w-16 text-right ${pctColor(asset.change_pct, isVol)}`}>
                  {fmtPct(asset.change_pct)}
                </span>
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}
