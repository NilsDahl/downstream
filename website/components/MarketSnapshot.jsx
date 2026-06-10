import RatesPanel      from './RatesPanel.jsx'
import FXPanel         from './FXPanel.jsx'
import CommoditiesPanel from './CommoditiesPanel.jsx'
import EquitiesPanel   from './EquitiesPanel.jsx'

export default function MarketSnapshot({ snapshot }) {
  if (!snapshot) return null

  return (
    <section>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <RatesPanel       rates={snapshot.rates} />
        <FXPanel          fx={snapshot.fx} />
        <CommoditiesPanel commodities={snapshot.commodities} />
        <EquitiesPanel    equities={snapshot.equities} />
      </div>
    </section>
  )
}
