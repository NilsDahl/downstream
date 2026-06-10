import fs from 'fs'
import path from 'path'
import matter from 'gray-matter'

// ─── Paths ───────────────────────────────────────────────────
const CONTENT_DIR  = path.join(process.cwd(), '..', 'content')
const DRAFTS_DIR   = path.join(CONTENT_DIR, 'drafts')
const SNAPSHOTS_DIR = path.join(CONTENT_DIR, 'snapshots')

// ─── Commodity units ─────────────────────────────────────────
const COMMODITY_UNITS = {
  brent: '/bbl', wti: '/bbl', natgas: '/MMBtu',
  rbob: '/gal',  heat_oil: '/gal',
  gold: '/oz',   silver: '/oz',  platinum: '/oz', palladium: '/oz',
  copper: '/lb',
  aluminium: '',  zinc_idx: '',  nickel_idx: '',  iron_ore: '',
  corn: '¢/bu',  wheat: '¢/bu', soybeans: '¢/bu',
  sugar: '¢/lb', coffee: '¢/lb', cotton: '¢/lb',
  lumber: '/mbf',
}

// ─── Rates display order ─────────────────────────────────────
const RATES_ORDER = {
  us:       ['us_sofr','us_t_1m','us_t_6m','us_t_1y','us_t_2y','us_t_5y','us_t_10y','us_t_30y'],
  eurozone: ['ez_estr','ez_3m','ez_6m','ez_1y','ez_2y','ez_5y','ez_10y','ez_30y'],
  germany:  ['de_2y','de_5y','de_10y','de_30y'],
  sweden:   ['se_swestr','se_2y','se_5y','se_7y','se_10y'],
  uk:       ['uk_sonia','uk_5y','uk_10y','uk_20y'],
  japan:    ['jp_2y','jp_5y','jp_10y','jp_30y'],
}

const FX_ORDER = {
  majors:    ['eurusd','gbpusd','usdjpy','usdchf','usdsek','usdnok','usddkk'],
  commodity: ['audusd','nzdusd','usdcad'],
  em:        ['usdcny','usdbrl','usdmxn','usdzar','usdtry'],
  cross:     ['eurgbp','eurjpy','eursek'],
  index:     ['dxy'],
}

const EQUITIES_ORDER = {
  us:         ['sp500','ndx','djia','rut'],
  europe:     ['stoxx50','dax','cac40','ftse100','omx30'],
  asia:       ['nikkei','hangseng','csi300','asx200'],
  em:         ['msci_em','bovespa','sensex'],
  volatility: ['vix'],
}

const COMMODITIES_ORDER = {
  energy:           ['brent','wti','natgas','rbob','heat_oil'],
  precious_metals:  ['gold','silver','platinum','palladium'],
  industrial_metals:['copper','aluminium','zinc_idx','nickel_idx','iron_ore'],
  agriculture:      ['corn','wheat','soybeans','sugar','coffee','cotton'],
  other:            ['lumber'],
}

// USD is the base currency (pair rises when dollar strengthens)
const USD_BASE_PAIRS = new Set([
  'usdjpy','usdchf','usdsek','usdnok','usddkk','usdcad',
  'usdcny','usdbrl','usdmxn','usdzar','usdinr','usdtry','usdkrw','usdsgd','dxy',
])

// ─── Snapshot transformation ──────────────────────────────────
function transformSnapshot(raw) {
  const assets = raw.assets || {}

  function pickGroup(orderMap, category) {
    const result = {}
    for (const [group, keys] of Object.entries(orderMap)) {
      result[group] = keys
        .filter(k => assets[k] && assets[k].category === category)
        .map(k => ({ key: k, ...assets[k] }))
        .filter(a => a.level != null || a.close != null)
    }
    return result
  }

  return {
    date: raw.date,
    rates:       pickGroup(RATES_ORDER,      'rates'),
    fx:          pickGroup(FX_ORDER,         'fx'),
    equities:    pickGroup(EQUITIES_ORDER,   'equities'),
    commodities: enrichCommodities(assets),
  }
}

function enrichCommodities(assets) {
  const result = {}
  for (const [group, keys] of Object.entries(COMMODITIES_ORDER)) {
    result[group] = keys
      .filter(k => assets[k])
      .map(k => ({
        key: k,
        unit: COMMODITY_UNITS[k] ?? '',
        ...assets[k],
      }))
      .filter(a => a.close != null)
  }
  return result
}

// ─── Markdown chain parser ───────────────────────────────────
export function parseChain(content) {
  // Remove h1 title if present
  const body = content.replace(/^#[^\n]+\n/, '').trim()

  // Driver
  const driverMatch = body.match(/\*\*The driver:\*\*[^\S\n]*(.+?)(?=\n\n|\n---)/s)
  const driver = driverMatch ? driverMatch[1].trim() : ''

  // Bounds of chain section
  const chainStart = body.indexOf('**The chain:**')
  const watchStart = body.indexOf('**What to watch:**')
  if (chainStart === -1) return { driver, nodes: [], watchText: '' }

  const chainSection = body.slice(
    chainStart + '**The chain:**'.length,
    watchStart !== -1 ? watchStart : undefined,
  )

  // Each node: **Label:** body  (body ends at next **Label:** or end)
  const nodes = []
  const nodeRe = /\*\*([^*\n]+):\*\*\s+([\s\S]*?)(?=\n\n\*\*[^*\n]+:\*\*|$)/g
  let m
  while ((m = nodeRe.exec(chainSection)) !== null) {
    const label = m[1].trim()
    const bodyText = m[2].trim()
    if (label && bodyText) nodes.push({ label, body: bodyText })
  }

  // What to watch text
  const watchText = watchStart !== -1
    ? body.slice(watchStart + '**What to watch:**'.length).replace(/^[\s\-—]+/, '').trim()
    : ''

  return { driver, nodes, watchText }
}

// ─── Biggest movers (for archive cards) ───────────────────────
function getBiggestMovers(snapshot, n = 4) {
  const assets = snapshot.assets || {}
  const moves = []
  for (const [key, asset] of Object.entries(assets)) {
    const pct = asset.change_pct
    const bps = asset.change_bps
    if (pct != null && Math.abs(pct) >= 0.01) {
      moves.push({ label: asset.label, pct, isBps: false })
    } else if (bps != null && Math.abs(bps) >= 1) {
      moves.push({ label: asset.label, pct: bps / 100, isBps: true, bps })
    }
  }
  moves.sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct))
  return moves.slice(0, n).map(m => {
    const sign = m.pct > 0 ? '+' : ''
    const val  = m.isBps
      ? `${sign}${m.bps.toFixed(0)}bp`
      : `${sign}${m.pct.toFixed(1)}%`
    return { label: m.label, val, positive: m.pct > 0 }
  })
}

// ─── Public API ──────────────────────────────────────────────

export function getAllDates() {
  if (!fs.existsSync(DRAFTS_DIR)) return []
  return fs.readdirSync(DRAFTS_DIR)
    .filter(f => f.endsWith('.md'))
    .map(f => f.replace('.md', ''))
    .sort((a, b) => b.localeCompare(a))  // newest first
}

export function getIssue(date) {
  const draftPath    = path.join(DRAFTS_DIR, `${date}.md`)
  const snapshotPath = path.join(SNAPSHOTS_DIR, `${date}.json`)

  if (!fs.existsSync(draftPath)) return null

  const { data: frontmatter, content } = matter(fs.readFileSync(draftPath, 'utf8'))
  const rawSnapshot = fs.existsSync(snapshotPath)
    ? JSON.parse(fs.readFileSync(snapshotPath, 'utf8'))
    : null

  const chain    = parseChain(content)
  const snapshot = rawSnapshot ? transformSnapshot(rawSnapshot) : null

  return { date, frontmatter, content, chain, snapshot }
}

export function getLatestIssue() {
  const dates = getAllDates()
  if (dates.length === 0) return null
  return getIssue(dates[0])
}

export function getAllIssues() {
  return getAllDates().map(date => {
    const draftPath    = path.join(DRAFTS_DIR, `${date}.md`)
    const snapshotPath = path.join(SNAPSHOTS_DIR, `${date}.json`)
    const { data: frontmatter, content } = matter(fs.readFileSync(draftPath, 'utf8'))
    const { driver } = parseChain(content)
    const rawSnapshot = fs.existsSync(snapshotPath)
      ? JSON.parse(fs.readFileSync(snapshotPath, 'utf8'))
      : null
    const movers = rawSnapshot ? getBiggestMovers(rawSnapshot) : []
    return { date, frontmatter, driver, movers }
  })
}

// Helper for FX color logic (exported for use in components)
export function fxIsPositiveForDollar(key, changePct) {
  if (changePct == null) return null
  if (USD_BASE_PAIRS.has(key)) {
    // USD/XXX: rising = stronger dollar
    return changePct > 0
  }
  // XXX/USD: falling = stronger dollar
  return changePct < 0
}
