# Downstream

**Daily macro implication chain analysis. Follow the chain.**

Trace cause-and-effect through financial markets: not "oil up 3%" — but oil up → inflation expectations shift → Fed pauses → bonds sell off → EUR/USD drops.

---

## What this is

Downstream is a two-part system:

```
PIPELINE (Python)                WEBSITE (Next.js)
─────────────────────            ──────────────────────────
fetch_data.py                    reads /content/ at build time
  → content/snapshots/           renders market snapshot panels
generate_draft.py                renders implication chain graphic
  → content/drafts/              renders full analysis prose
run_daily.py (orchestrator)
```

The pipeline runs daily and writes files. The website reads those files and renders them as a static site. Nothing talks to a database — the pipeline and website communicate only through flat files in `/content/`.

---

## Project structure

```
downstream/
├── pipeline/
│   ├── fetch_data.py         pulls market data → JSON snapshot
│   ├── generate_draft.py     calls Claude API → markdown draft
│   ├── run_daily.py          orchestrates both, scheduled 09:30
│   └── requirements.txt
├── content/
│   ├── snapshots/            YYYY-MM-DD.json  (one per trading day)
│   └── drafts/               YYYY-MM-DD.md    (one per trading day)
└── website/
    ├── app/
    │   ├── layout.jsx        root layout, fonts
    │   ├── page.jsx          homepage
    │   ├── globals.css       Tailwind v4 design tokens
    │   └── issue/[date]/
    │       └── page.jsx      individual issue page
    ├── components/
    │   ├── Header.jsx
    │   ├── MarketSnapshot.jsx   2×2 panel grid container
    │   ├── RatesPanel.jsx       yield curves, bp logic
    │   ├── FXPanel.jsx          FX pairs, dollar color logic
    │   ├── CommoditiesPanel.jsx prices with units
    │   ├── EquitiesPanel.jsx    indices + volatility
    │   ├── ImplicationChain.jsx visual chain graphic
    │   ├── IssueBody.jsx        markdown prose renderer
    │   └── Archive.jsx          grid of past issues
    └── lib/
        ├── content.js        server-only: reads files, transforms data, parses chain
        └── utils.js          client-safe: FX dollar-strength color logic
```

---

## Environment variables

Create `.env.local` in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
FRED_API_KEY=...
```

FRED key is free at [fred.stlouisfed.org](https://fred.stlouisfed.org).
All other data sources (ECB, Riksbank, Bundesbank, BoJ, BoE) are keyless.

---

## Running the pipeline

```bash
cd pipeline
pip install -r requirements.txt          # first time only

python run_daily.py                      # fetch + draft in one shot
python run_daily.py --schedule           # print the crontab line

# Or run steps individually:
python fetch_data.py                     # → content/snapshots/YYYY-MM-DD.json
python generate_draft.py                 # → content/drafts/YYYY-MM-DD.md
python generate_draft.py path/to/file.json   # use a specific snapshot
```

**Python environment:** uses `.venv/` with Homebrew Python 3.12 (not miniconda, which has a broken numpy on this machine).

```bash
# To activate:
source .venv/bin/activate

# To recreate:
/usr/local/bin/python3.12 -m venv .venv
.venv/bin/pip install -r pipeline/requirements.txt
```

---

## Running the website

```bash
cd website
npm install          # first time only
npm run dev          # → http://localhost:3000 (hot reload)
npm run build        # production build (pre-renders all pages)
```

---

## The pipeline in depth

### fetch_data.py

Fetches 93 assets across 6 economies. Each asset is written to the snapshot JSON with this structure:

**Rate assets** (yield curves):
```json
"us_t_10y": {
  "label":        "US 10Y",
  "category":     "rates",
  "sub_category": "us",
  "source":       "FRED",
  "series_id":    "DGS10",
  "as_of":        "2026-06-10",
  "level":        4.56,
  "prev_level":   4.55,
  "change_bps":   1.0
}
```

**Price assets** (FX, equities, commodities):
```json
"eurusd": {
  "label":        "EUR/USD",
  "category":     "fx",
  "sub_category": "majors",
  "source":       "yfinance",
  "ticker":       "EURUSD=X",
  "as_of":        "2026-06-10",
  "close":        1.1563,
  "prev_close":   1.1521,
  "change_pct":   0.303
}
```

### Data sources

| Source | Assets | API details |
|---|---|---|
| **FRED** | SOFR, US Treasuries (1M, 6M, 1Y, 2Y, 5Y, 10Y, 30Y) | Requires `FRED_API_KEY`. Series: `SOFR`, `DGS1MO`, `DGS6MO`, `DGS1`, `DGS2`, `DGS5`, `DGS10`, `DGS30` |
| **ECB API** | €STR, ECB AAA euro area yield curve (3M–30Y) | No key. Base: `data-api.ecb.europa.eu`. €STR: `EST/B.EU000A2X2A25.WT`. Curve: `YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_{tenor}` |
| **Riksbank API** | SWESTR, Swedish govt bonds (2Y, 5Y, 7Y, 10Y) | No key. SWESTR: `api.riksbank.se/swestr/v1/all/SWESTR`. Bonds: `api.riksbank.se/swea/v1/Observations/{id}/{from}/{to}`. Series: `SEGVB2YC`, `SEGVB5YC`, `SEGVB7YC`, `SEGVB10YC` |
| **Bundesbank API** | German Bunds (2Y, 5Y, 10Y, 30Y) | No key. New API: `api.statistiken.bundesbank.de/rest/data/BBSIS`. Dataflow: `BBSIS` (Umlaufsrenditen/Zinsstrukturkurve). Key pattern: `D.I.ZST.ZI.EUR.S1311.B.A604.R{NN}XX.R.A.A._Z._Z.A` where `NN` = maturity in years (`02`, `05`, `10`, `30`). **Note:** old API (`api.bundesbank.de`) shuts down 2026-06-30. |
| **Bank of England** | SONIA, UK Gilts zero-coupon (5Y, 10Y, 20Y) | No key. CSV endpoint: `bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp`. Series: `IUDSOIA` (SONIA), `IUDSNZC` (5Y), `IUDMNZC` (10Y), `IUDLNZC` (20Y) |
| **Japan MoF** | JGBs (2Y, 5Y, 10Y, 30Y) | No key. CSV: `mof.go.jp/english/jgbs/reference/interest_rate/jgbcme.csv` (current month) + `historical/jgbcme_all.csv` (fallback if <2 rows) |
| **yfinance** | All FX pairs, equity indices, commodities | No key. See `YFINANCE_TICKERS` dict in `fetch_data.py` |

### Non-obvious data quality decisions

**Zero-volume filter for futures**: For futures contracts (tickers ending in `=F`), days with zero trading volume are stale carry-forward prices — the contract has effectively stopped trading. We skip those days when computing the daily change. Without this, contract rolls create fake price gaps: aluminium appeared to drop 9% one day because the front-month contract expired and the new one opened at a different price.

**Aluminium and Iron Ore**: `ALI=F` (COMEX Aluminium) and `TIO=F` (Iron Ore CME) are illiquid and unreliable. We use `ALUM.L` (WisdomTree Aluminium ETC, LSE) and `IRON.L` (WisdomTree Iron Ore ETC, LSE) instead. These have real daily volume and track LME/spot prices reliably.

**Zinc and Nickel**: LME futures are not available on yfinance. We use `ZINC.L` (WisdomTree Zinc ETC) and `^SPGSIK` (S&P GSCI Nickel index) as proxies.

**BDI (Baltic Dry Index)**: Not available on any free source. Bloomberg or Nasdaq Data Link (paid) required.

**VSTOXX**: Not available via yfinance API despite appearing on the Yahoo Finance website.

**SSL on macOS**: Python's cert store is not linked to the system keychain when installed via Homebrew. We set `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` to the `certifi` path at startup.

### generate_draft.py

Reads the snapshot, builds a prompt, calls `claude-sonnet-4-6`.

**System prompt rules (summarised):**
- Identify the primary driver first (largest, most anomalous, or most explanatory move)
- Build the chain outward from the driver, naming mechanisms not just directions
- If two moves contradict, name the tension explicitly — don't paper over it
- Every number cited must be copied verbatim from the snapshot (prevents hallucination)
- Close with "What to watch": specific, falsifiable signals — not vague commentary
- Forbidden: "it remains to be seen", "investors will be watching", "in this environment", "navigating uncertainty"

**Output format:**
```markdown
---
date: YYYY-MM-DD
model: claude-sonnet-4-6
---

**The driver:** [one sentence with exact figure from snapshot]

**The chain:**

**[Node label]:** [2–4 sentences explaining the mechanism]

**[Node label]:** [2–4 sentences]

[4–6 nodes total]

**What to watch:** [2–3 sentences, specific and falsifiable]
```

---

## The website in depth

Built with **Next.js 16** (app router) + **Tailwind CSS v4**.

### Architecture: static site generation (SSG)

When you run `npm run build`, Next.js reads all draft/snapshot files and pre-renders every page to static HTML. No server runs at request time. This means:
- Near-instant page loads
- No database, no server, no authentication
- Deploys trivially to Vercel

The homepage (`/`) shows the latest issue. Each past issue has its own URL at `/issue/YYYY-MM-DD`. `generateStaticParams()` in `app/issue/[date]/page.jsx` tells Next.js which dates to build.

**Breaking change in Next.js 16:** `params` in dynamic routes is a Promise — must be `await`ed. Old Next.js 14 code passes params directly and will break.

### lib/content.js — the data layer

Server-only file (uses Node.js `fs`). Three jobs:

**1. Reads files:**
```javascript
getAllDates()     → ['2026-06-10', '2026-06-09', ...]
getIssue(date)   → { date, snapshot, chain, content }
getLatestIssue() → getIssue(getAllDates()[0])
getAllIssues()    → summary objects for archive cards
```

**2. Transforms the flat snapshot into panel-ready grouped structures:**

The snapshot JSON has one flat `assets` object (93 entries, all mixed together). The website needs them grouped, ordered, and enriched. `content.js` reorganizes:
```
snapshot.rates.us       → [SOFR, 1M, 6M, 1Y, 2Y, 5Y, 10Y, 30Y]
snapshot.rates.germany  → [Bund 2Y, Bund 5Y, Bund 10Y, Bund 30Y]
snapshot.fx.majors      → [EUR/USD, GBP/USD, USD/JPY, ...]
snapshot.commodities.precious_metals → [Gold, Silver, Platinum, Palladium]
```
It also attaches commodity display units (`/bbl`, `/oz`, `¢/bu`, etc.).

**3. Parses the markdown chain structure:**

Uses a regex to extract `**Label:** body` paragraphs from the draft into `{ label, body }` objects that `ImplicationChain.jsx` can render as visual cards.

### Color logic

The financial color choices are deliberately non-naive:

**Rates panel — red = yields rose, green = yields fell**
A +8bp move on the 10Y is a tightening signal — bad for bonds. Coloring it red despite being "a positive number" is correct economically.

**FX panel — red = dollar strengthened, green = dollar weakened**
The rule: *does a rising change_pct mean the dollar got stronger?*
- `EUR/USD` up → dollar weakened → **green**
- `USD/JPY` up → dollar strengthened → **red**
- `DXY` up → dollar strengthened → **red**
This makes every FX pair tell a consistent dollar story regardless of how the pair is quoted.

**Equities — standard, except volatility is inverted**
VIX rising = fear = bad → **red**. VIX falling = calm = good → **green**.

### Tailwind v4 configuration

There is no `tailwind.config.js`. In Tailwind v4, custom tokens live directly in `globals.css` using the `@theme` block:
```css
@import "tailwindcss";

@theme {
  --color-parchment:  #FAF7F2;
  --color-amber:      #D97706;
  --color-up:         #16A34A;
  --color-down:       #DC2626;
  --color-border:     #E8E0D0;
  --font-serif: var(--font-playfair), Georgia, serif;
  --font-mono:  var(--font-jetbrains), ui-monospace, monospace;
}
```
Tailwind auto-generates `bg-parchment`, `text-amber`, `font-serif`, `text-up`, `text-down`, etc.

### Fonts

Playfair Display (serif headlines) and JetBrains Mono (all data and numbers) are loaded in `app/layout.jsx` via `next/font/google`. Next.js self-hosts the font files — no request goes to Google Fonts at runtime, which is better for privacy and performance.

---

## Deploying to Vercel

1. Push the whole repo to GitHub
2. Connect to Vercel, set **Root Directory** to `website`
3. Add environment variables: `ANTHROPIC_API_KEY`, `FRED_API_KEY`
4. Vercel will auto-build on every push

The `../content/` relative path works because Vercel includes the full repo at build time — from `website/`, the `content/` directory is one level up at `../content/`.

After each daily pipeline run, commit and push `content/drafts/` and `content/snapshots/` to trigger a Vercel rebuild.

---

## Known gaps and limitations

| Gap | Reason | Workaround |
|---|---|---|
| German Bunds (old API) | `api.bundesbank.de` shuts down 2026-06-30 | Already migrated to `api.statistiken.bundesbank.de/rest/data/BBSIS` |
| VSTOXX | Not available via yfinance API | No free source found |
| Zinc futures | LME not on yfinance | Using `ZINC.L` ETC as proxy |
| Nickel futures | LME not on yfinance | Using `^SPGSIK` GSCI index as proxy |
| BDI | No free API | Needs Bloomberg or Nasdaq Data Link (paid) |
| BoE Gilts | Only 5Y, 10Y, 20Y available via IADB | No 1Y, 2Y, or 30Y series on BoE's free API |
| SWESTR | Not on FRED | Using Riksbank's dedicated `swestr/v1` API directly |

---

## Author

Master's student at Stockholm School of Economics. Works at the Riksbank producing SWESTR daily. Background in fixed income, FX, rates, futures, and commodities.
