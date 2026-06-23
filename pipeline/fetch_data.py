"""
fetch_data.py — comprehensive market data fetcher for Downstream.

Source architecture
-------------------
FRED          : US rates — SOFR, Treasury curve 1M-30Y        (key required)
ECB API       : €STR, eurozone AAA curve 3M-30Y               (no key)
Riksbank API  : SWESTR, Swedish govt bonds 2Y-10Y             (no key)
BoE IADB      : SONIA, UK Gilts zero-coupon 5Y/10Y/20Y       (no key)
Bundesbank    : German Bunds 2Y/5Y/10Y/30Y (Svensson spots)  (no key)
Japan MoF CSV : JGB yields 2Y/5Y/10Y/30Y                     (no key)
Alpha Vantage : Commodities — energy, metals, agriculture      (key required, 25 calls/day)
Twelve Data   : FX pairs, equity indices, bond fallbacks       (key required, 800 calls/day)
yfinance      : Last-resort fallback only                      (no key, often rate-limited)

Notes on coverage gaps
----------------------
- BoE gilts: only 5Y, 10Y, 20Y; no 1Y/2Y/30Y on the IADB endpoint
- ECB curve: shortest tenor is 3M (no 1M spot rate on the AAA curve)
- BDI (Baltic Dry): no free API — needs Bloomberg / Nasdaq Data Link
- AV free tier: 25 calls/day, 5/min → 12 s delay enforced between commodity calls
- TD free tier: 800 calls/day, entire FX+equity batch fits in one call

Output: /content/snapshots/YYYY-MM-DD.json
Each asset record includes source, as_of, and is_fresh (True if as_of is the
most recent business day) so the website can flag stale data visually.
"""

import json
import math
import os
import random
import sys
import time
from datetime import date, timedelta

import certifi
import requests
import yfinance as yf

# Fix SSL certificate verification on macOS (Homebrew Python cert store is
# not linked to the system keychain by default).
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
# Asset registry  (label, category, sub_category)
# ─────────────────────────────────────────────────────────────
ASSET_META = {
    # US yield curve
    "us_sofr":    ("SOFR",             "rates", "us"),
    "us_t_1m":    ("US 1M",            "rates", "us"),
    "us_t_6m":    ("US 6M",            "rates", "us"),
    "us_t_1y":    ("US 1Y",            "rates", "us"),
    "us_t_2y":    ("US 2Y",            "rates", "us"),
    "us_t_5y":    ("US 5Y",            "rates", "us"),
    "us_t_10y":   ("US 10Y",           "rates", "us"),
    "us_t_30y":   ("US 30Y",           "rates", "us"),
    # Eurozone yield curve (ECB AAA)
    "ez_estr":    ("€STR",             "rates", "eurozone"),
    "ez_3m":      ("EZ 3M",            "rates", "eurozone"),
    "ez_6m":      ("EZ 6M",            "rates", "eurozone"),
    "ez_1y":      ("EZ 1Y",            "rates", "eurozone"),
    "ez_2y":      ("EZ 2Y",            "rates", "eurozone"),
    "ez_5y":      ("EZ 5Y",            "rates", "eurozone"),
    "ez_10y":     ("EZ 10Y",           "rates", "eurozone"),
    "ez_30y":     ("EZ 30Y",           "rates", "eurozone"),
    # German Bunds (Bundesbank SDMX API)
    "de_2y":      ("Bund 2Y",          "rates", "germany"),
    "de_5y":      ("Bund 5Y",          "rates", "germany"),
    "de_10y":     ("Bund 10Y",         "rates", "germany"),
    "de_30y":     ("Bund 30Y",         "rates", "germany"),
    # Swedish yield curve
    "se_swestr":  ("SWESTR",           "rates", "sweden"),
    "se_2y":      ("SE 2Y",            "rates", "sweden"),
    "se_5y":      ("SE 5Y",            "rates", "sweden"),
    "se_7y":      ("SE 7Y",            "rates", "sweden"),
    "se_10y":     ("SE 10Y",           "rates", "sweden"),
    # UK yield curve (BoE zero-coupon)
    "uk_sonia":   ("SONIA",            "rates", "uk"),
    "uk_5y":      ("Gilt 5Y",          "rates", "uk"),
    "uk_10y":     ("Gilt 10Y",         "rates", "uk"),
    "uk_20y":     ("Gilt 20Y",         "rates", "uk"),
    # Japan yield curve (MoF CSV)
    "jp_2y":      ("JGB 2Y",           "rates", "japan"),
    "jp_5y":      ("JGB 5Y",           "rates", "japan"),
    "jp_10y":     ("JGB 10Y",          "rates", "japan"),
    "jp_30y":     ("JGB 30Y",          "rates", "japan"),
    # FX — majors
    "eurusd":     ("EUR/USD",          "fx", "majors"),
    "gbpusd":     ("GBP/USD",          "fx", "majors"),
    "usdjpy":     ("USD/JPY",          "fx", "majors"),
    "usdchf":     ("USD/CHF",          "fx", "majors"),
    "usdsek":     ("USD/SEK",          "fx", "majors"),
    "usdnok":     ("USD/NOK",          "fx", "majors"),
    "usddkk":     ("USD/DKK",          "fx", "majors"),
    # FX — commodity currencies
    "audusd":     ("AUD/USD",          "fx", "commodity"),
    "nzdusd":     ("NZD/USD",          "fx", "commodity"),
    "usdcad":     ("USD/CAD",          "fx", "commodity"),
    # FX — EM
    "usdcny":     ("USD/CNY",          "fx", "em"),
    "usdbrl":     ("USD/BRL",          "fx", "em"),
    "usdmxn":     ("USD/MXN",          "fx", "em"),
    "usdzar":     ("USD/ZAR",          "fx", "em"),
    "usdinr":     ("USD/INR",          "fx", "em"),
    "usdtry":     ("USD/TRY",          "fx", "em"),
    "usdkrw":     ("USD/KRW",          "fx", "em"),
    "usdsgd":     ("USD/SGD",          "fx", "em"),
    # FX — cross rates
    "eurgbp":     ("EUR/GBP",          "fx", "cross"),
    "eurjpy":     ("EUR/JPY",          "fx", "cross"),
    "eursek":     ("EUR/SEK",          "fx", "cross"),
    # Dollar index
    "dxy":        ("DXY",              "fx", "index"),
    # Equities — US
    "sp500":      ("S&P 500",          "equities", "us"),
    "ndx":        ("Nasdaq 100",       "equities", "us"),
    "djia":       ("Dow Jones",        "equities", "us"),
    "rut":        ("Russell 2000",     "equities", "us"),
    # Equities — Europe
    "stoxx50":    ("Euro Stoxx 50",    "equities", "europe"),
    "dax":        ("DAX",              "equities", "europe"),
    "cac40":      ("CAC 40",           "equities", "europe"),
    "ftse100":    ("FTSE 100",         "equities", "europe"),
    "omx30":      ("OMX Stockholm 30", "equities", "europe"),
    # Equities — Asia
    "nikkei":     ("Nikkei 225",       "equities", "asia"),
    "hangseng":   ("Hang Seng",        "equities", "asia"),
    "csi300":     ("CSI 300",          "equities", "asia"),
    "asx200":     ("ASX 200",          "equities", "asia"),
    # Equities — EM
    "msci_em":    ("MSCI EM",          "equities", "em"),
    "bovespa":    ("Bovespa",          "equities", "em"),
    "sensex":     ("Sensex",           "equities", "em"),
    # Volatility
    "vix":        ("VIX",              "equities", "volatility"),
    # vstoxx: no reliable free ticker — omitted until source found
    # Commodities — energy
    "brent":      ("Brent Crude",      "commodities", "energy"),
    "wti":        ("WTI Crude",        "commodities", "energy"),
    "natgas":     ("Natural Gas",      "commodities", "energy"),
    "rbob":       ("Gasoline (RBOB)",  "commodities", "energy"),
    "heat_oil":   ("Heating Oil",      "commodities", "energy"),
    # Commodities — precious metals
    "gold":       ("Gold",             "commodities", "precious_metals"),
    "silver":     ("Silver",           "commodities", "precious_metals"),
    "platinum":   ("Platinum",         "commodities", "precious_metals"),
    "palladium":  ("Palladium",        "commodities", "precious_metals"),
    # Commodities — industrial metals
    "copper":     ("Copper",           "commodities", "industrial_metals"),
    "aluminium":  ("Aluminium",        "commodities", "industrial_metals"),
    "zinc_idx":   ("Zinc (LSE)",        "commodities", "industrial_metals"),
    "nickel_idx": ("Nickel (GSCI)",    "commodities", "industrial_metals"),
    "iron_ore":   ("Iron Ore",         "commodities", "industrial_metals"),
    # Commodities — agriculture
    "corn":       ("Corn",             "commodities", "agriculture"),
    "wheat":      ("Wheat",            "commodities", "agriculture"),
    "soybeans":   ("Soybeans",         "commodities", "agriculture"),
    "sugar":      ("Sugar",            "commodities", "agriculture"),
    "coffee":     ("Coffee",           "commodities", "agriculture"),
    "cotton":     ("Cotton",           "commodities", "agriculture"),
    # Commodities — other
    "lumber":     ("Lumber",           "commodities", "other"),
    # BDI intentionally omitted — no free API (needs Bloomberg / Nasdaq Data Link)
}

RATE_ASSETS = {k for k, (_, cat, _) in ASSET_META.items() if cat == "rates"}

# ─────────────────────────────────────────────────────────────
# Twelve Data ticker map  (replaces yfinance)
# ─────────────────────────────────────────────────────────────
TD_API_URL = "https://api.twelvedata.com/quote"

TD_TICKERS = {
    # ── FX pairs (all confirmed on free tier) ──────────────────
    "eurusd":    "EUR/USD",
    "gbpusd":    "GBP/USD",
    "usdjpy":    "USD/JPY",
    "usdchf":    "USD/CHF",
    "usdsek":    "USD/SEK",
    "usdnok":    "USD/NOK",
    "usddkk":    "USD/DKK",
    "audusd":    "AUD/USD",
    "nzdusd":    "NZD/USD",
    "usdcad":    "USD/CAD",
    "usdcny":    "USD/CNY",
    "usdbrl":    "USD/BRL",
    "usdmxn":    "USD/MXN",
    "usdzar":    "USD/ZAR",
    "usdinr":    "USD/INR",
    "usdtry":    "USD/TRY",
    "usdkrw":    "USD/KRW",
    "usdsgd":    "USD/SGD",
    "eurgbp":    "EUR/GBP",
    "eurjpy":    "EUR/JPY",
    "eursek":    "EUR/SEK",
    # ── Precious metals as FX (XAU confirmed; XAG/XPT/XPD need paid) ──
    "gold":      "XAU/USD",
    # ── Equity indices: SPX/NDX/FTSE require paid TD plan;
    #    others return "index unavailable" on free tier.
    #    Omitted here — handled by yfinance fallback. ────────────
    # ── Commodities: energy/base metals confirmed; others need paid ──
    "brent":     "BRENT",
    "wti":       "WTI",
    "natgas":    "NATGAS",
    "copper":    "COPPER",
    "aluminium": "ALUMINIUM",
    # ── German Bunds fallback (primary: Bundesbank API) ───────
    "de_2y":    "DE2Y",
    "de_5y":    "DE5Y",
    "de_10y":   "DE10Y",
    "de_30y":   "DE30Y",
    # ── JGB fallback (primary: Japan MoF CSV) ──────────────────
    "jp_2y":    "JP2Y",
    "jp_5y":    "JP5Y",
    "jp_10y":   "JP10Y",
    "jp_30y":   "JP30Y",
}

# ─────────────────────────────────────────────────────────────
# Alpha Vantage — commodity functions (primary for commodities)
# Free tier: 25 calls/day, 5 calls/min → enforce 12 s between calls
# ─────────────────────────────────────────────────────────────
AV_API_URL = "https://www.alphavantage.co/query"

AV_COMMODITY_FUNCTIONS = {
    "wti":       "WTI",
    "brent":     "BRENT",
    "natgas":    "NATURAL_GAS",
    "copper":    "COPPER",
    "aluminium": "ALUMINUM",
    "corn":      "CORN",
    "wheat":     "WHEAT",
    "cotton":    "COTTON",
    "sugar":     "SUGAR",
    "coffee":    "COFFEE",
}

# ─────────────────────────────────────────────────────────────
# yfinance ticker map  (last-resort fallback only)
# ─────────────────────────────────────────────────────────────
# US Treasury yield tickers available same-day on Yahoo Finance.
# These OVERRIDE the FRED T+1 data fetched in step 1 so the yield
# changes shown in the snapshot match the same session as equities/FX.
# Yahoo quotes yields in percentage points (4.493 = 4.493%).
# No Yahoo ticker exists for 2Y, 1Y, 6M, 1M — those stay on FRED.
YF_TREASURY_OVERRIDES = {
    "us_t_10y": "^TNX",
    "us_t_30y": "^TYX",
    "us_t_5y":  "^FVX",
    "us_t_1m":  "^IRX",   # 13-week T-bill; closest free proxy for short end
}

YFINANCE_TICKERS = {
    # German Bunds: =RR tickers no longer served by Yahoo Finance — omitted
    # JGBs: =RR tickers no longer served by Yahoo Finance — omitted
    # FX
    "eurusd":     "EURUSD=X",
    "gbpusd":     "GBPUSD=X",
    "usdjpy":     "JPY=X",
    "usdchf":     "CHF=X",
    "usdsek":     "SEK=X",
    "usdnok":     "NOK=X",
    "usddkk":     "DKK=X",
    "audusd":     "AUDUSD=X",
    "nzdusd":     "NZDUSD=X",
    "usdcad":     "CAD=X",
    "usdcny":     "CNY=X",
    "usdbrl":     "BRL=X",
    "usdmxn":     "MXN=X",
    "usdzar":     "ZAR=X",
    "usdinr":     "INR=X",
    "usdtry":     "TRY=X",
    "usdkrw":     "KRW=X",
    "usdsgd":     "SGD=X",
    "eurgbp":     "EURGBP=X",
    "eurjpy":     "EURJPY=X",
    "eursek":     "EURSEK=X",
    "dxy":        "DX-Y.NYB",
    # Equities
    "sp500":      "^GSPC",
    "ndx":        "^NDX",
    "djia":       "^DJI",
    "rut":        "^RUT",
    "stoxx50":    "^STOXX50E",
    "dax":        "^GDAXI",
    "cac40":      "^FCHI",
    "ftse100":    "^FTSE",
    "omx30":      "^OMX",
    "nikkei":     "^N225",
    "hangseng":   "^HSI",
    "csi300":     "000300.SS",
    "asx200":     "^AXJO",
    "msci_em":    "EEM",
    "bovespa":    "^BVSP",
    "sensex":     "^BSESN",
    "vix":        "^VIX",
    # vstoxx: no working ticker on yfinance currently
    # Commodities — energy
    "brent":      "BZ=F",
    "wti":        "CL=F",
    "natgas":     "NG=F",
    "rbob":       "RB=F",
    "heat_oil":   "HO=F",
    # Commodities — precious metals
    "gold":       "GC=F",
    "silver":     "SI=F",
    "platinum":   "PL=F",
    "palladium":  "PA=F",
    # Commodities — industrial metals
    "copper":     "HG=F",
    "aluminium":  "ALUM.L",    # WisdomTree Aluminium ETC (LSE, USD) — ALI=F illiquid
    "zinc_idx":   "ZINC.L",    # WisdomTree Zinc ETC (LSE)
    "nickel_idx": "^SPGSIK",   # S&P GSCI Nickel Index (LME futures not on yfinance)
    "iron_ore":   "IRON.L",    # WisdomTree Iron Ore ETC (LSE) — TIO=F has zero volume
    # Commodities — agriculture
    "corn":       "ZC=F",
    "wheat":      "ZW=F",
    "soybeans":   "ZS=F",
    "sugar":      "SB=F",
    "coffee":     "KC=F",
    "cotton":     "CT=F",
    # Commodities — other
    "lumber":     "LBR=F",
}

# FRED series IDs for US yield curve
FRED_SERIES = {
    "us_sofr":  "SOFR",
    "us_t_1m":  "DGS1MO",
    "us_t_6m":  "DGS6MO",
    "us_t_1y":  "DGS1",
    "us_t_2y":  "DGS2",
    "us_t_5y":  "DGS5",
    "us_t_10y": "DGS10",
    "us_t_30y": "DGS30",
}

# ECB API series keys
ECB_BASE = "https://data-api.ecb.europa.eu/service/data"
ECB_SERIES = {
    "ez_estr": "EST/B.EU000A2X2A25.WT",
    "ez_3m":   "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_3M",
    "ez_6m":   "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_6M",
    "ez_1y":   "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_1Y",
    "ez_2y":   "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y",
    "ez_5y":   "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_5Y",
    "ez_10y":  "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",
    "ez_30y":  "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_30Y",
}

# Riksbank series IDs
RIKSBANK_BOND_SERIES = {
    "se_2y":  "SEGVB2YC",
    "se_5y":  "SEGVB5YC",
    "se_7y":  "SEGVB7YC",
    "se_10y": "SEGVB10YC",
}

# BoE IADB series codes
BOE_SERIES = {
    "uk_sonia": "IUDSOIA",
    "uk_5y":    "IUDSNZC",
    "uk_10y":   "IUDMNZC",
    "uk_20y":   "IUDLNZC",
}


# ─────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────

def _clean(val):
    """Convert NaN/inf → None for JSON safety."""
    if val is None:
        return None
    try:
        if math.isnan(val) or math.isinf(val):
            return None
    except TypeError:
        pass
    return val


def _pct(prev, curr):
    if prev and curr and prev != 0:
        return round((curr - prev) / abs(prev) * 100, 4)
    return None


def _bps(prev, curr):
    if prev is not None and curr is not None:
        return round((curr - prev) * 100, 2)
    return None


def _is_fresh(as_of: str) -> bool:
    """True if as_of is the most recent business day (handles weekends)."""
    if not as_of:
        return False
    today = date.today()
    # Allow up to 4 calendar days to cover weekends and public holidays
    cutoff = (today - timedelta(days=4)).isoformat()
    return as_of >= cutoff


def _record(key: str, source: str, **kwargs) -> dict:
    label, category, sub_category = ASSET_META[key]
    cleaned = {k: _clean(v) for k, v in kwargs.items()}
    return {
        "label":        label,
        "category":     category,
        "sub_category": sub_category,
        "source":       source,
        "is_fresh":     _is_fresh(str(cleaned.get("as_of", ""))),
        **cleaned,
    }


def _warn(msg: str):
    print(f"  [warn] {msg}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────
# Fetcher: yfinance (batch download)
# ─────────────────────────────────────────────────────────────

def _yf_parse_df(key: str, ticker: str, df) -> dict | None:
    """Turn a Close/Volume DataFrame into a snapshot record. Returns None on failure."""
    df = df[df["Close"].notna()].copy()
    if len(df) < 2:
        return None

    # Futures-specific quality filters
    if ticker.endswith("=F") and "Volume" in df.columns:
        # Drop zero-volume bars (stale carry-forward / dead contracts)
        traded = df[df["Volume"] > 0]
        if len(traded) >= 2:
            df = traded
        elif len(traded) == 1:
            last_idx = df.index.get_loc(traded.index[-1])
            if last_idx >= 1:
                df = df.iloc[last_idx - 1 : last_idx + 1]

        if len(df) < 2:
            return None

        # Detect likely contract rolls: very large move + volume on the last bar
        # is less than 20% of the prior 3-bar average → probable roll, not real move
        if len(df) >= 3 and "Volume" in df.columns:
            last_vol = float(df["Volume"].iloc[-1])
            avg_prev = float(df["Volume"].iloc[-4:-1].mean()) if len(df) >= 4 else float(df["Volume"].iloc[:-1].mean())
            last_close = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2])
            pct_move   = abs(last_close - prev_close) / abs(prev_close) * 100 if prev_close else 0
            if pct_move > 4 and avg_prev > 0 and last_vol < 0.25 * avg_prev:
                _warn(f"yfinance: {key} ({ticker}) flagged as likely roll "
                      f"({pct_move:.1f}% move, vol={last_vol:.0f} vs avg={avg_prev:.0f}) — skipping")
                return None

    prev  = float(df["Close"].iloc[-2])
    last  = float(df["Close"].iloc[-1])
    as_of = df.index[-1].strftime("%Y-%m-%d")

    if _clean(last) is None or _clean(prev) is None:
        return None

    if key in RATE_ASSETS:
        return _record(key, "yfinance", ticker=ticker, as_of=as_of,
            level=round(last, 4), prev_level=round(prev, 4),
            change_bps=_bps(prev, last))
    else:
        return _record(key, "yfinance", ticker=ticker, as_of=as_of,
            close=round(last, 6), prev_close=round(prev, 6),
            change_pct=_pct(prev, last))


def fetch_yfinance(keys_tickers: dict[str, str]) -> dict[str, dict]:
    if not keys_tickers:
        return {}

    tickers = list(keys_tickers.values())
    key_map = {v: k for k, v in keys_tickers.items()}   # ticker → key

    # Batch download
    results = {}
    failed_tickers = set()
    try:
        raw = yf.download(
            tickers, period="5d", auto_adjust=True,
            progress=False, threads=True, group_by="ticker",
        )
        for ticker, key in key_map.items():
            try:
                if len(tickers) == 1:
                    df = raw[["Close", "Volume"]].copy()
                elif ticker not in raw.columns.get_level_values(0):
                    failed_tickers.add(ticker)
                    continue
                else:
                    df = raw[ticker][["Close", "Volume"]].copy()

                record = _yf_parse_df(key, ticker, df)
                if record:
                    results[key] = record
                else:
                    failed_tickers.add(ticker)
            except Exception:
                failed_tickers.add(ticker)
    except Exception as exc:
        _warn(f"yfinance batch download failed: {exc}")
        failed_tickers = set(tickers)

    # Individual retry for anything that failed in the batch — pace to avoid rate limits
    if failed_tickers:
        _warn(f"yfinance: retrying {len(failed_tickers)} tickers individually")
        for ticker in failed_tickers:
            time.sleep(random.uniform(1.5, 3.0))
            key = key_map[ticker]
            try:
                hist = yf.Ticker(ticker).history(period="7d", auto_adjust=True)
                if hist.empty:
                    _warn(f"yfinance: no data for {key} ({ticker})")
                    continue
                df = hist[["Close", "Volume"]].copy()
                record = _yf_parse_df(key, ticker, df)
                if record:
                    results[key] = record
                else:
                    _warn(f"yfinance: {key} ({ticker}) still failed after retry")
            except Exception as exc:
                _warn(f"yfinance retry error for {key} ({ticker}): {exc}")

    return results


# ─────────────────────────────────────────────────────────────
# Fetcher: Twelve Data
# ─────────────────────────────────────────────────────────────

def fetch_twelvedata(keys_tickers: dict[str, str]) -> dict[str, dict]:
    api_key = os.environ.get("TWELVEDATA_API_KEY", "")
    if not api_key:
        _warn("TWELVEDATA_API_KEY not set — skipping Twelve Data fetch")
        return {}
    if not keys_tickers:
        return {}

    results = {}
    items = list(keys_tickers.items())

    # Free tier: 8 credits/minute (1 credit per symbol in batch).
    # Chunk to 8 symbols and sleep 62 s between chunks to stay within limit.
    chunk_size = 8
    for batch_idx, i in enumerate(range(0, len(items), chunk_size)):
        if batch_idx > 0:
            time.sleep(62)

        chunk = dict(items[i : i + chunk_size])
        ticker_to_key = {v: k for k, v in chunk.items()}
        symbol_str = ",".join(chunk.values())

        try:
            resp = requests.get(
                TD_API_URL,
                params={"symbol": symbol_str, "apikey": api_key},
                timeout=30,
            )
            if resp.status_code == 429:
                _warn(f"Twelve Data rate limit hit on batch {batch_idx + 1} — stopping")
                break
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            _warn(f"Twelve Data batch {batch_idx + 1} error: {exc}")
            continue

        # Single-symbol response is unwrapped; multi-symbol is keyed by symbol
        if len(chunk) == 1:
            data = {list(chunk.values())[0]: data}

        for td_symbol, q in data.items():
            key = ticker_to_key.get(td_symbol)
            if not key:
                continue
            if not isinstance(q, dict):
                continue
            if q.get("code") == 429:
                _warn(f"Twelve Data rate limit within batch — stopping")
                return results
            if q.get("status") == "error":
                _warn(f"twelvedata: {key} ({td_symbol}): {q.get('message', 'unknown error')}")
                continue

            try:
                last  = float(q["close"])
                prev  = float(q["previous_close"])
                as_of = str(q.get("datetime", ""))[:10]
            except (KeyError, TypeError, ValueError) as exc:
                _warn(f"twelvedata: {key} ({td_symbol}): parse error — {exc}")
                continue

            if _clean(last) is None or _clean(prev) is None:
                continue

            if key in RATE_ASSETS:
                results[key] = _record(key, "twelvedata", ticker=td_symbol, as_of=as_of,
                    level=round(last, 4), prev_level=round(prev, 4),
                    change_bps=_bps(prev, last))
            else:
                results[key] = _record(key, "twelvedata", ticker=td_symbol, as_of=as_of,
                    close=round(last, 6), prev_close=round(prev, 6),
                    change_pct=_pct(prev, last))

    return results


# ─────────────────────────────────────────────────────────────
# Fetcher: Alpha Vantage (commodities)
# ─────────────────────────────────────────────────────────────

def fetch_alphavantage(keys_needed: set[str]) -> dict[str, dict]:
    api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
    if not api_key:
        _warn("ALPHAVANTAGE_API_KEY not set — skipping Alpha Vantage fetch")
        return {}

    to_fetch = {k: fn for k, fn in AV_COMMODITY_FUNCTIONS.items() if k in keys_needed}
    if not to_fetch:
        return {}

    results = {}
    for i, (key, function) in enumerate(to_fetch.items()):
        if i > 0:
            time.sleep(15)  # stay safely under 5 calls/min on free tier
        try:
            resp = requests.get(
                AV_API_URL,
                params={"function": function, "interval": "daily", "apikey": api_key},
                timeout=20,
            )
            resp.raise_for_status()
            body = resp.json()
        except Exception as exc:
            _warn(f"Alpha Vantage {key} ({function}): {exc}")
            continue

        if "Information" in body:
            _warn(f"Alpha Vantage rate limit hit: {body['Information'][:80]}")
            break
        if "data" not in body:
            _warn(f"Alpha Vantage {key}: unexpected response — {list(body.keys())}")
            continue

        rows = [r for r in body["data"] if r.get("value") not in (None, ".", "")]
        if len(rows) < 2:
            _warn(f"Alpha Vantage {key}: insufficient data ({len(rows)} rows)")
            continue

        try:
            last  = float(rows[0]["value"])
            prev  = float(rows[1]["value"])
            as_of = rows[0]["date"]
        except (KeyError, ValueError) as exc:
            _warn(f"Alpha Vantage {key}: parse error — {exc}")
            continue

        if _clean(last) is None or _clean(prev) is None:
            continue

        results[key] = _record(key, "AlphaVantage", function=function, as_of=as_of,
            close=round(last, 6), prev_close=round(prev, 6),
            change_pct=_pct(prev, last))

    return results


# ─────────────────────────────────────────────────────────────
# Fetcher: FRED
# ─────────────────────────────────────────────────────────────

def fetch_fred(fred) -> dict[str, dict]:
    results = {}
    for key, series_id in FRED_SERIES.items():
        try:
            series = fred.get_series_latest_release(series_id).dropna()
            if len(series) < 2:
                _warn(f"FRED {key}: insufficient data")
                continue
            prev  = float(series.iloc[-2])
            last  = float(series.iloc[-1])
            as_of = series.index[-1].strftime("%Y-%m-%d")
            results[key] = _record(key, "FRED",
                series_id=series_id, as_of=as_of,
                level=round(last, 4), prev_level=round(prev, 4),
                change_bps=_bps(prev, last))
        except Exception as exc:
            _warn(f"FRED {key} ({series_id}): {exc}")
    return results


# ─────────────────────────────────────────────────────────────
# Fetcher: ECB API
# ─────────────────────────────────────────────────────────────

def _ecb_fetch(series_key: str) -> tuple[float, float, str] | None:
    base_url = f"{ECB_BASE}/{series_key}?lastNObservations=2"

    # Try JSON first
    try:
        r = requests.get(f"{base_url}&format=jsondata", timeout=15,
                         headers={"Accept": "application/json"},
                         verify=certifi.where())
        r.raise_for_status()
        body        = r.json()
        series_dict = body["dataSets"][0]["series"]
        if series_dict:                                    # ECB sometimes returns {}
            series_k    = next(iter(series_dict))
            obs         = series_dict[series_k]["observations"]
            dates       = body["structure"]["dimensions"]["observation"][0]["values"]
            sorted_keys = sorted(obs.keys(), key=int)
            if len(sorted_keys) >= 2:
                prev  = float(obs[sorted_keys[-2]][0])
                last  = float(obs[sorted_keys[-1]][0])
                as_of = dates[int(sorted_keys[-1])]["id"]
                return prev, last, as_of
    except Exception:
        pass

    # Fall back to XML — ECB JSON occasionally returns empty series
    try:
        import re as _re
        r = requests.get(base_url, timeout=15,
                         headers={"Accept": "application/xml"},
                         verify=certifi.where())
        r.raise_for_status()
        vals  = _re.findall(r'ObsValue value="([^"]+)"', r.text)
        dates = _re.findall(r'ObsDimension value="([^"]+)"', r.text)
        if len(vals) >= 2 and len(dates) >= 2:
            prev  = float(vals[-2])
            last  = float(vals[-1])
            as_of = dates[-1]
            return prev, last, as_of
    except Exception:
        pass

    return None


def fetch_ecb() -> dict[str, dict]:
    results = {}
    for key, series_key in ECB_SERIES.items():
        result = _ecb_fetch(series_key)
        if result is None:
            _warn(f"ECB {key}: fetch failed")
            continue
        prev, last, as_of = result
        results[key] = _record(key, "ECB",
            series_key=series_key, as_of=as_of,
            level=round(last, 4), prev_level=round(prev, 4),
            change_bps=_bps(prev, last))
    return results


# ─────────────────────────────────────────────────────────────
# Fetcher: Riksbank API
# ─────────────────────────────────────────────────────────────

def fetch_riksbank() -> dict[str, dict]:
    results = {}
    lookback = (date.today() - timedelta(days=14)).isoformat()
    today    = date.today().isoformat()

    # SWESTR — dedicated API endpoint
    try:
        r = requests.get(
            "https://api.riksbank.se/swestr/v1/all/SWESTR",
            params={"fromDate": lookback, "toDate": today},
            timeout=15, verify=certifi.where(),
        )
        r.raise_for_status()
        obs = [d for d in r.json() if d.get("rate") is not None]
        if len(obs) >= 2:
            prev  = float(obs[-2]["rate"])
            last  = float(obs[-1]["rate"])
            as_of = obs[-1]["date"]
            results["se_swestr"] = _record("se_swestr", "Riksbank",
                as_of=as_of,
                level=round(last, 4), prev_level=round(prev, 4),
                change_bps=_bps(prev, last))
        else:
            _warn("Riksbank SWESTR: insufficient data")
    except Exception as exc:
        _warn(f"Riksbank SWESTR: {exc}")

    # Government bond yields
    for key, series_id in RIKSBANK_BOND_SERIES.items():
        try:
            url = (f"https://api.riksbank.se/swea/v1/Observations/"
                   f"{series_id}/{lookback}/{today}")
            r   = requests.get(url, timeout=15, verify=certifi.where())
            r.raise_for_status()
            obs = [d for d in r.json() if d.get("value") is not None]
            if len(obs) < 2:
                _warn(f"Riksbank {key}: insufficient data")
                continue
            prev  = float(obs[-2]["value"])
            last  = float(obs[-1]["value"])
            as_of = obs[-1]["date"]
            results[key] = _record(key, "Riksbank",
                series_id=series_id, as_of=as_of,
                level=round(last, 4), prev_level=round(prev, 4),
                change_bps=_bps(prev, last))
        except Exception as exc:
            _warn(f"Riksbank {key} ({series_id}): {exc}")

    return results


# ─────────────────────────────────────────────────────────────
# Fetcher: Bank of England IADB
# ─────────────────────────────────────────────────────────────

BOE_URL = ("https://www.bankofengland.co.uk/boeapps/database/"
           "_iadb-fromshowcolumns.asp")

def fetch_boe() -> dict[str, dict]:
    from_date = (date.today() - timedelta(days=14)).strftime("%d/%b/%Y")
    to_date   = date.today().strftime("%d/%b/%Y")
    params = {
        "csv.x":       "yes",
        "SeriesCodes": ",".join(BOE_SERIES.values()),
        "UsingCodes":  "Y",
        "CSVF":        "TN",
        "Datefrom":    from_date,
        "Dateto":      to_date,
    }
    headers = {
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 Chrome/124 Safari/537.36"),
        "Accept": "text/html,*/*;q=0.8",
    }
    results = {}
    try:
        r = requests.get(BOE_URL, params=params, headers=headers,
                         timeout=20, verify=certifi.where())
        r.raise_for_status()
        lines = [l for l in r.text.strip().splitlines() if l.strip()]
        if len(lines) < 3:
            _warn("BoE: empty or malformed CSV")
            return results

        header_cols = lines[0].split(",")
        code_to_col = {c.strip(): i for i, c in enumerate(header_cols)}
        code_to_key = {v: k for k, v in BOE_SERIES.items()}
        series_obs: dict[str, list[tuple[str, float]]] = {k: [] for k in BOE_SERIES}

        def _boe_date(raw: str) -> str:
            """Normalise BoE date strings ('16 Jun 2026') to ISO-8601."""
            from datetime import datetime as _dt
            try:
                return _dt.strptime(raw.strip(), "%d %b %Y").strftime("%Y-%m-%d")
            except ValueError:
                return raw.strip()

        for line in lines[1:]:
            parts    = line.split(",")
            row_date = _boe_date(parts[0])
            for code, key in code_to_key.items():
                idx = code_to_col.get(code)
                if idx is None or idx >= len(parts):
                    continue
                val_str = parts[idx].strip()
                if not val_str or val_str == ".":
                    continue
                try:
                    series_obs[key].append((row_date, float(val_str)))
                except ValueError:
                    pass

        for key, obs in series_obs.items():
            if len(obs) < 2:
                _warn(f"BoE {key}: only {len(obs)} observations")
                continue
            prev  = obs[-2][1]
            last  = obs[-1][1]
            as_of = obs[-1][0]
            results[key] = _record(key, "BoE",
                as_of=as_of,
                level=round(last, 4), prev_level=round(prev, 4),
                change_bps=_bps(prev, last))
    except Exception as exc:
        _warn(f"BoE fetch failed: {exc}")

    return results


# ─────────────────────────────────────────────────────────────
# Fetcher: Deutsche Bundesbank — BBSIS dataflow
# ─────────────────────────────────────────────────────────────
# Zinsstrukturkurve (Svensson spot rates) for börsennotierte Bundeswertpapiere.
# Source: api.statistiken.bundesbank.de, dataflow BBSIS
# Key pattern: BBSIS.D.I.ZST.ZI.EUR.S1311.B.A604.R{NN}XX.R.A.A._Z._Z.A
# where NN = maturity in years (02, 05, 10, 30 etc.)
BBK_BASE = "https://api.statistiken.bundesbank.de/rest/data/BBSIS"

BBK_SERIES = {
    "de_2y":  "D.I.ZST.ZI.EUR.S1311.B.A604.R02XX.R.A.A._Z._Z.A",
    "de_5y":  "D.I.ZST.ZI.EUR.S1311.B.A604.R05XX.R.A.A._Z._Z.A",
    "de_10y": "D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A",
    "de_30y": "D.I.ZST.ZI.EUR.S1311.B.A604.R30XX.R.A.A._Z._Z.A",
}


def fetch_bundesbank() -> dict[str, dict]:
    results = {}
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; Downstream/1.0)",
        "Accept":     "text/csv",
    })
    for key, sdmx_key in BBK_SERIES.items():
        try:
            r = s.get(f"{BBK_BASE}/{sdmx_key}",
                      params={"lastNObservations": 3},
                      timeout=15, verify=certifi.where())
            if not r.ok:
                _warn(f"Bundesbank {key}: HTTP {r.status_code}")
                continue
            lines = [l for l in r.text.splitlines() if l.strip()]
            if len(lines) < 3:
                _warn(f"Bundesbank {key}: insufficient rows")
                continue
            header   = lines[0].lstrip("﻿").split(";")
            period_c = header.index("TIME_PERIOD") if "TIME_PERIOD" in header else 7
            val_c    = header.index("OBS_VALUE")   if "OBS_VALUE"   in header else 8
            rows = []
            for line in lines[1:]:
                p = line.split(";")
                if len(p) > max(period_c, val_c):
                    try:
                        rows.append((p[period_c], float(p[val_c])))
                    except ValueError:
                        pass
            if len(rows) < 2:
                _warn(f"Bundesbank {key}: fewer than 2 valid observations")
                continue
            prev_date, prev = rows[-2]
            last_date, last = rows[-1]
            results[key] = _record(key, "Bundesbank",
                series_key=sdmx_key, as_of=last_date,
                level=round(last, 4), prev_level=round(prev, 4),
                change_bps=_bps(prev, last))
        except Exception as exc:
            _warn(f"Bundesbank {key}: {exc}")
    return results


# ─────────────────────────────────────────────────────────────
# Fetcher: Japan MoF JGB yields (CSV)
# ─────────────────────────────────────────────────────────────
# Monthly rolling CSV (current month) + full historical CSV as fallback.
# Columns: Date, 1Y, 2Y, 3Y, 4Y, 5Y, 6Y, 7Y, 8Y, 9Y, 10Y, 15Y, 20Y, 25Y, 30Y, 40Y
MOF_CURRENT_URL    = "https://www.mof.go.jp/english/jgbs/reference/interest_rate/jgbcme.csv"
MOF_HISTORICAL_URL = "https://www.mof.go.jp/english/jgbs/reference/interest_rate/historical/jgbcme_all.csv"
MOF_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Downstream/1.0)"}

JGB_COL_MAP = {
    "jp_2y":  "2Y",
    "jp_5y":  "5Y",
    "jp_10y": "10Y",
    "jp_30y": "30Y",
}


def _parse_mof_csv(text: str) -> list[dict]:
    """Parse MoF CSV into list of {date, 1Y, 2Y, ...} dicts, newest-last."""
    rows = []
    header = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Date"):
            header = [c.strip() for c in line.split(",")]
            continue
        if header is None:
            continue
        # Skip footer notes
        parts = line.split(",")
        if not parts[0][:4].isdigit():
            continue
        row = {"date": parts[0].strip()}
        for i, col in enumerate(header[1:], start=1):
            if i < len(parts) and parts[i].strip():
                try:
                    row[col] = float(parts[i].strip())
                except ValueError:
                    pass
        if len(row) > 1:
            rows.append(row)
    return rows


def fetch_mof_jgb() -> dict[str, dict]:
    # Try current-month CSV first (small, fast)
    rows = []
    try:
        r = requests.get(MOF_CURRENT_URL, timeout=15, verify=certifi.where(),
                         headers=MOF_HEADERS)
        r.raise_for_status()
        rows = _parse_mof_csv(r.text)
    except Exception as exc:
        _warn(f"MoF current CSV: {exc}")

    # If fewer than 2 data rows (first business day of month), load historical
    if len(rows) < 2:
        try:
            r = requests.get(MOF_HISTORICAL_URL, timeout=30, verify=certifi.where(),
                             headers=MOF_HEADERS)
            r.raise_for_status()
            hist_rows = _parse_mof_csv(r.text)
            # Prepend historical rows that aren't already in current
            current_dates = {row["date"] for row in rows}
            rows = [r for r in hist_rows if r["date"] not in current_dates] + rows
        except Exception as exc:
            _warn(f"MoF historical CSV: {exc}")

    if len(rows) < 2:
        _warn("MoF JGB: could not obtain 2 observations")
        return {}

    prev_row = rows[-2]
    last_row = rows[-1]
    as_of    = last_row["date"]

    results = {}
    for key, col in JGB_COL_MAP.items():
        prev = prev_row.get(col)
        last = last_row.get(col)
        if prev is None or last is None:
            _warn(f"MoF JGB {key}: missing column {col}")
            continue
        results[key] = _record(key, "MoF Japan",
            as_of=as_of,
            level=round(last, 4), prev_level=round(prev, 4),
            change_bps=_bps(prev, last))
    return results


# ─────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────

def build_snapshot() -> dict[str, dict]:
    data: dict[str, dict] = {}

    # 1. FRED — US yield curve
    fred_key = os.environ.get("FRED_API_KEY", "")
    if fred_key and FRED_AVAILABLE:
        try:
            fred = Fred(api_key=fred_key)
            print("  [FRED] fetching US yield curve …")
            fetched = fetch_fred(fred)
            data.update(fetched)
            print(f"         {len(fetched)}/{len(FRED_SERIES)} series")
        except Exception as exc:
            _warn(f"FRED init: {exc}")
    else:
        _warn("FRED_API_KEY not set — US yield curve skipped")

    # 1b. yfinance — override FRED T+1 US Treasury yields with same-day data
    #     ^TNX/^TYX/^FVX/^IRX are live during the session; this makes US
    #     yields consistent in time with equities/FX in the same snapshot.
    print("  [yfinance] US Treasury yield overrides …")
    yf_tsy = fetch_yfinance(YF_TREASURY_OVERRIDES)
    data.update(yf_tsy)   # intentional overwrite of FRED data
    print(f"             {len(yf_tsy)}/{len(YF_TREASURY_OVERRIDES)} overrides")

    # 2. ECB — Eurozone yield curve + €STR
    print("  [ECB]      fetching Eurozone curve + €STR …")
    fetched = fetch_ecb()
    data.update(fetched)
    print(f"             {len(fetched)}/{len(ECB_SERIES)} series")

    # 3. Riksbank — SWESTR + Swedish govt bonds
    print("  [Riksbank] fetching Swedish rates …")
    fetched = fetch_riksbank()
    data.update(fetched)
    print(f"             {len(fetched)} series")

    # 4. BoE — SONIA + Gilts
    print("  [BoE]      fetching UK rates …")
    fetched = fetch_boe()
    data.update(fetched)
    print(f"             {len(fetched)} series")

    # 5. Bundesbank — German Bund yield curve
    print("  [Bundesbank] fetching German Bund curve …")
    fetched = fetch_bundesbank()
    data.update(fetched)
    print(f"               {len(fetched)}/{len(BBK_SERIES)} series")

    # 6. Japan MoF — JGB yield curve
    print("  [MoF Japan]  fetching JGB curve …")
    fetched = fetch_mof_jgb()
    data.update(fetched)
    print(f"               {len(fetched)}/{len(JGB_COL_MAP)} series")

    # 7. yfinance — primary for FX, equities, commodities
    yf_needed = {k: v for k, v in YFINANCE_TICKERS.items() if k not in data}
    print(f"  [yfinance] fetching {len(yf_needed)} assets …")
    fetched = fetch_yfinance(yf_needed)
    data.update(fetched)
    print(f"             {len(fetched)}/{len(yf_needed)} assets")

    # 8. Alpha Vantage — commodity fallback for anything yfinance missed
    av_needed = {k for k in AV_COMMODITY_FUNCTIONS if k not in data}
    if av_needed:
        print(f"  [Alpha Vantage] fallback for {len(av_needed)} commodities …")
        fetched = fetch_alphavantage(av_needed)
        data.update(fetched)
        print(f"                  {len(fetched)}/{len(av_needed)} commodities")

    # 9. Twelve Data — fallback for FX + remaining assets yfinance/AV missed
    td_needed = {k: v for k, v in TD_TICKERS.items() if k not in data}
    if td_needed:
        print(f"  [Twelve Data] fallback for {len(td_needed)} assets …")
        fetched = fetch_twelvedata(td_needed)
        data.update(fetched)
        print(f"                {len(fetched)}/{len(td_needed)} assets")

    return data


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main():
    snapshot_dir = os.path.join(
        os.path.dirname(__file__), "..", "content", "snapshots"
    )
    os.makedirs(snapshot_dir, exist_ok=True)

    today    = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else date.today().isoformat()
    out_path = os.path.join(snapshot_dir, f"{today}.json")

    print(f"\nDownstream fetch — {today}")
    print("=" * 52)
    data = build_snapshot()
    print("=" * 52)

    total   = len(ASSET_META)
    fetched = len(data)
    missing = [k for k in ASSET_META if k not in data]

    payload = {"date": today, "assets": data}
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nSnapshot  → {out_path}")
    print(f"Coverage  : {fetched}/{total}")
    if missing:
        print(f"Missing   : {', '.join(missing)}")

    return out_path


if __name__ == "__main__":
    main()
