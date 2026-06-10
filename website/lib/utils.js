// Client-safe utilities (no Node.js imports)

const USD_BASE_PAIRS = new Set([
  'usdjpy','usdchf','usdsek','usdnok','usddkk','usdcad',
  'usdcny','usdbrl','usdmxn','usdzar','usdinr','usdtry','usdkrw','usdsgd','dxy',
])

// Returns true if a rising change_pct means the dollar strengthened.
// Used for coloring: dollar stronger = red.
export function fxDollarStrengthened(key, changePct) {
  if (changePct == null) return null
  if (USD_BASE_PAIRS.has(key)) return changePct > 0   // USD/XXX rises → dollar up
  return changePct < 0                                  // XXX/USD falls → dollar up
}
