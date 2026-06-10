'use client'
import { useState } from 'react'

const GROUP_LABELS = {
  energy:            'Energy',
  precious_metals:   'Precious Metals',
  industrial_metals: 'Industrial Metals',
  agriculture:       'Agriculture',
  other:             'Other',
}

function fmtPrice(close, unit) {
  if (close == null) return '—'
  // Cents-per-unit commodities (corn, wheat, etc.)
  if (unit && unit.startsWith('¢')) {
    return `${close.toFixed(0)}${unit}`
  }
  // ETCs/indices — just show level
  if (!unit || unit === '') {
    return close.toFixed(3)
  }
  // Dollar-denominated: use $ prefix
  if (close >= 1000) return `$${Math.round(close).toLocaleString('en-US')}${unit}`
  if (close >= 10)   return `$${close.toFixed(2)}${unit}`
  return `$${close.toFixed(3)}${unit}`
}

function fmtPct(v) {
  if (v == null) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

function pctColor(v) {
  if (v == null) return 'text-ink-muted'
  if (v > 0) return 'text-up'
  if (v < 0) return 'text-down'
  return 'text-ink-muted'
}

export default function CommoditiesPanel({ commodities }) {
  const [collapsed, setCollapsed] = useState({})
  if (!commodities) return null

  const toggle = (key) => setCollapsed(c => ({ ...c, [key]: !c[key] }))

  return (
    <div className="bg-white rounded-lg shadow-sm border border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h2 className="font-mono text-xs font-bold uppercase tracking-widest text-ink">
          Commodities
        </h2>
        <div className="flex gap-4 font-mono text-[10px] text-ink-muted uppercase tracking-wider">
          <span className="w-24 text-right">Price</span>
          <span className="w-16 text-right">Δ</span>
        </div>
      </div>
      {Object.entries(commodities).map(([group, rows]) => {
        if (!rows || rows.length === 0) return null
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
                <span className="font-mono text-xs text-ink w-24 text-right">
                  {fmtPrice(asset.close, asset.unit)}
                </span>
                <span className={`font-mono text-xs w-16 text-right ${pctColor(asset.change_pct)}`}>
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
