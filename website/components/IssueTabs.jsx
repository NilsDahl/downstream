'use client'
import { useState } from 'react'
import MarketSnapshot   from './MarketSnapshot.jsx'
import ImplicationChain from './ImplicationChain.jsx'
import NewsTab          from './NewsTab.jsx'
import Archive          from './Archive.jsx'

const TABS = ['Implication Chains', 'Data', 'News', 'Archive']

function TabButton({ label, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`pb-3 text-sm font-medium transition-colors border-b-2 whitespace-nowrap cursor-pointer select-none ${
        active
          ? 'border-primary text-foreground'
          : 'border-transparent text-subtle hover:text-muted-foreground'
      }`}
    >
      {label}
    </button>
  )
}

export default function IssueTabs({ chains, newsSummary, snapshot, allIssues }) {
  const [active, setActive] = useState('Implication Chains')

  return (
    <div>
      <div className="flex gap-6 border-b border-border mb-8 overflow-x-auto">
        {TABS.map(t => (
          <TabButton key={t} label={t} active={active === t} onClick={() => setActive(t)} />
        ))}
      </div>

      {active === 'Implication Chains' && <ImplicationChain chains={chains} />}
      {active === 'Data'               && <MarketSnapshot snapshot={snapshot} />}
      {active === 'News'               && <NewsTab newsSummary={newsSummary} />}
      {active === 'Archive'            && <Archive issues={allIssues} />}
    </div>
  )
}
