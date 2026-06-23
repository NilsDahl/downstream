const ABBREV = {
  'FRED':         'FRED',
  'ECB':          'ECB',
  'Riksbank':     'RIX',
  'BoE':          'BoE',
  'Bundesbank':   'BBK',
  'MoF Japan':    'MoF',
  'yfinance':     'YF',
  'twelvedata':   'TD',
  'AlphaVantage': 'AV',
}

export default function SourceTag({ source, missing }) {
  if (missing) {
    return (
      <span className="ml-1.5 text-[9px] font-mono text-amber-500/80 tracking-wide">
        no data
      </span>
    )
  }
  if (!source) return null
  const abbrev = ABBREV[source] ?? source
  return (
    <span className="ml-1.5 text-[9px] font-mono text-muted-foreground/50 tracking-wide">
      {abbrev}
    </span>
  )
}
