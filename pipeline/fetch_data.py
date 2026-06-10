"""
fetch_data.py — comprehensive market data fetcher for Downstream.

Sources
-------
FRED        : SOFR, US Treasury curve (1M, 6M, 1Y, 2Y, 5Y, 10Y, 30Y)
ECB API     : €STR, ECB AAA euro area govt bond curve (3M, 6M, 1Y, 2Y, 5Y, 10Y, 30Y)
Riksbank API: SWESTR, Swedish govt bonds (2Y, 5Y, 7Y, 10Y)
BoE IADB    : SONIA, UK Gilts zero-coupon (5Y, 10Y, 20Y)
yfinance    : German Bunds, JGBs, all FX, equities, commodities

Notes on coverage gaps
----------------------
- Zinc / Nickel: LME futures unavailable on yfinance; using DJ/GSCI index proxies
- BDI (Baltic Dry Index): not available on any free source; needs paid API
- German Bunds / JGBs: via Reuters =RR tickers on yfinance (may be sparse)
- BoE gilts: only 5Y, 10Y, 20Y available via IADB; no 1Y/2Y/30Y series
- ECB curve: shortest tenor is 3M (no 1M spot rate on the AAA curve)

Output: /content/snapshots/YYYY-MM-DD.json
"""

import json
import math
import os
import sys
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
# yfinance ticker map
# ─────────────────────────────────────────────────────────────
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


def _record(key: str, source: str, **kwargs) -> dict:
    label, category, sub_category = ASSET_META[key]
    return {
        "label":        label,
        "category":     category,
        "sub_category": sub_category,
        "source":       source,
        **{k: _clean(v) for k, v in kwargs.items()},
    }


def _warn(msg: str):
    print(f"  [warn] {msg}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────
# Fetcher: yfinance (batch download)
# ─────────────────────────────────────────────────────────────

def fetch_yfinance(keys_tickers: dict[str, str]) -> dict[str, dict]:
    if not keys_tickers:
        return {}

    tickers = list(keys_tickers.values())
    key_map = {v: k for k, v in keys_tickers.items()}   # ticker → key

    try:
        raw = yf.download(
            tickers, period="5d", auto_adjust=True,
            progress=False, threads=True, group_by="ticker",
        )
    except Exception as exc:
        _warn(f"yfinance download failed: {exc}")
        return {}

    results = {}
    for ticker, key in key_map.items():
        try:
            # Handle both single-ticker (flat) and multi-ticker (MultiIndex) DataFrames
            if isinstance(raw.columns, type(None)) or len(tickers) == 1:
                df = raw[["Close", "Volume"]].copy()
            else:
                if ticker not in raw.columns.get_level_values(0):
                    _warn(f"yfinance: no data for {key} ({ticker})")
                    continue
                df = raw[ticker][["Close", "Volume"]].copy()

            df = df[df["Close"].notna()]
            if len(df) < 2:
                _warn(f"yfinance: insufficient history for {key} ({ticker})")
                continue

            # For futures (ticker ends in =F): drop zero-volume bars — they are
            # stale carry-forward prices from illiquid or rolled contracts.
            if ticker.endswith("=F") and "Volume" in df.columns:
                traded = df[df["Volume"] > 0]
                if len(traded) >= 2:
                    df = traded
                elif len(traded) == 1:
                    # Keep at least 2 rows: last traded + the bar before it
                    last_idx = df.index.get_loc(traded.index[-1])
                    if last_idx >= 1:
                        df = df.iloc[last_idx - 1 : last_idx + 1]

            if len(df) < 2:
                _warn(f"yfinance: no traded data for {key} ({ticker})")
                continue

            prev  = float(df["Close"].iloc[-2])
            last  = float(df["Close"].iloc[-1])
            as_of = df.index[-1].strftime("%Y-%m-%d")

            if _clean(last) is None or _clean(prev) is None:
                _warn(f"yfinance: NaN price for {key} ({ticker})")
                continue

            if key in RATE_ASSETS:
                results[key] = _record(key, "yfinance",
                    ticker=ticker, as_of=as_of,
                    level=round(last, 4), prev_level=round(prev, 4),
                    change_bps=_bps(prev, last))
            else:
                results[key] = _record(key, "yfinance",
                    ticker=ticker, as_of=as_of,
                    close=round(last, 6), prev_close=round(prev, 6),
                    change_pct=_pct(prev, last))
        except Exception as exc:
            _warn(f"yfinance parse error for {key} ({ticker}): {exc}")

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
    url = f"{ECB_BASE}/{series_key}?lastNObservations=2&format=jsondata"
    try:
        r = requests.get(url, timeout=15,
                         headers={"Accept": "application/json"},
                         verify=certifi.where())
        r.raise_for_status()
        body   = r.json()
        # Series key varies by dataset depth — use whichever key is present
        series_dict = body["dataSets"][0]["series"]
        series_k    = next(iter(series_dict))
        obs         = series_dict[series_k]["observations"]
        dates  = body["structure"]["dimensions"]["observation"][0]["values"]
        sorted_keys = sorted(obs.keys(), key=int)
        if len(sorted_keys) < 2:
            return None
        prev  = float(obs[sorted_keys[-2]][0])
        last  = float(obs[sorted_keys[-1]][0])
        as_of = dates[int(sorted_keys[-1])]["id"]
        return prev, last, as_of
    except Exception:
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

        for line in lines[1:]:
            parts    = line.split(",")
            row_date = parts[0].strip()
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

    # 7. yfinance — everything not yet fetched
    yf_needed = {k: v for k, v in YFINANCE_TICKERS.items() if k not in data}
    print(f"  [yfinance] fetching {len(yf_needed)} assets …")
    fetched = fetch_yfinance(yf_needed)
    data.update(fetched)
    print(f"             {len(fetched)}/{len(yf_needed)} assets")

    return data


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main():
    snapshot_dir = os.path.join(
        os.path.dirname(__file__), "..", "content", "snapshots"
    )
    os.makedirs(snapshot_dir, exist_ok=True)

    today    = date.today().isoformat()
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
