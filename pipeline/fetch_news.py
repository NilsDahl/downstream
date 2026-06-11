"""
fetch_news.py — fetches relevant news headlines from NewsAPI.

Runs after fetch_data.py as part of the daily pipeline.
Requires NEWSAPI_KEY in the environment.

Output: /content/news/YYYY-MM-DD.json
"""

import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

import certifi
import requests

NEWSAPI_URL   = "https://newsapi.org/v2/everything"
CURRENTS_URL  = "https://api.currentsapi.services/v1/search"

# Maps URL domains to human-readable source names for Currents API articles
# (Currents doesn't return a source name field, only the article URL).
_DOMAIN_TO_SOURCE: dict[str, str] = {
    "reuters.com":        "Reuters",
    "bloomberg.com":      "Bloomberg",
    "ft.com":             "Financial Times",
    "wsj.com":            "The Wall Street Journal",
    "cnbc.com":           "CNBC",
    "marketwatch.com":    "MarketWatch",
    "economist.com":      "The Economist",
    "apnews.com":         "Associated Press",
    "barrons.com":        "Barron's",
    "seekingalpha.com":   "Seeking Alpha",
    "thestreet.com":      "TheStreet",
    "businessinsider.com":"Business Insider",
    "fortune.com":        "Fortune",
    "forbes.com":         "Forbes",
    "bbc.com":            "BBC News",
    "bbc.co.uk":          "BBC News",
    "theguardian.com":    "The Guardian",
    "nytimes.com":        "The New York Times",
    "washingtonpost.com": "The Washington Post",
    "axios.com":          "Axios",
    "politico.com":       "Politico",
    "npr.org":            "NPR",
    "cbsnews.com":        "CBS News",
    "nbcnews.com":        "NBC News",
    "abcnews.go.com":     "ABC News",
    "telegraph.co.uk":    "The Telegraph",
    "scmp.com":           "South China Morning Post",
    "aljazeera.com":      "Al Jazeera English",
    "financialpost.com":  "Financial Post",
    "ecb.europa.eu":      "European Central Bank",
    "federalreserve.gov": "Federal Reserve",
    "bankofengland.co.uk":"Bank of England",
    "riksbank.se":        "Riksbank",
    "boj.or.jp":          "Bank of Japan",
}

# Each query is assigned to a theme bucket. Bucket caps control how many
# headlines from each theme reach the final output.
QUERY_BUCKETS: dict[str, str] = {
    "Federal Reserve OR Fed rate OR FOMC":              "central_banks",
    "ECB OR European Central Bank OR Lagarde":          "central_banks",
    "Bank of England OR BOE OR Bailey":                 "central_banks",
    "Bank of Japan OR BOJ OR Ueda":                     "central_banks",
    "Riksbank OR Swedish central bank":                 "central_banks",
    "PBOC OR People's Bank of China":                   "central_banks",

    "Treasury bonds OR yield curve OR UST":             "rates_credit",
    "inflation OR CPI OR PCE":                          "rates_credit",
    "interest rates OR rate cut OR rate hike":          "rates_credit",
    "credit spreads OR high yield OR investment grade": "rates_credit",

    "oil price OR crude OR OPEC OR Brent":              "commodities_energy",
    "natural gas OR LNG":                               "commodities_energy",

    "gold price OR precious metals":                    "commodities_metals",
    "copper OR industrial metals":                      "commodities_metals",

    "wheat OR corn OR soybeans OR food prices":         "commodities_agri",

    "dollar index OR DXY OR dollar strength":           "fx_macro",
    "euro dollar OR EURUSD":                            "fx_macro",
    "emerging markets OR EM currency":                  "fx_macro",
    "China economy OR GDP OR property market":          "fx_macro",

    "geopolitical risk OR sanctions OR trade war":      "risk_geopolitics",
    "recession OR economic slowdown OR PMI":            "risk_geopolitics",
    "VIX OR market volatility OR risk off":             "risk_geopolitics",
    "earnings OR corporate profits":                    "risk_geopolitics",
}

# Global cap on final output after all filtering, scoring, and dedup.
GLOBAL_HEADLINE_CAP = 40

# Domain allowlist passed to NewsAPI — only articles from these outlets are
# returned. Using `domains` instead of `sources` removes the 20-source cap.
_QUALITY_DOMAINS = ",".join([
    # Specialist financial / wire services
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com",
    "cnbc.com", "marketwatch.com", "economist.com", "apnews.com",
    "barrons.com", "seekingalpha.com", "thestreet.com",
    "fxstreet.com", "investing.com", "morningstar.com",
    # Quality general / international business press
    "businessinsider.com", "fortune.com", "forbes.com",
    "bbc.com", "bbc.co.uk", "theguardian.com", "nytimes.com",
    "washingtonpost.com", "axios.com", "politico.com", "npr.org",
    "telegraph.co.uk", "thetimes.co.uk", "abcnews.go.com",
    "cbsnews.com", "nbcnews.com", "scmp.com", "asia.nikkei.com",
    "handelsblatt.com", "financialpost.com", "aljazeera.com",
])

SOURCE_TIER: dict[str, int] = {
    # Tier 3 — specialist financial / wire services
    "Reuters": 3,
    "Bloomberg": 3,
    "Financial Times": 3,
    "The Wall Street Journal": 3,
    "Wall Street Journal": 3,
    "The Economist": 3,
    "CNBC": 3,
    "MarketWatch": 3,
    "Associated Press": 3,
    "Barron's": 3,
    "Dow Jones": 3,
    "Investor's Business Daily": 3,
    "FXStreet": 3,
    "Seeking Alpha": 3,

    # Tier 2 — quality general / international business press
    "BBC News": 2,
    "BBC": 2,
    "The Guardian": 2,
    "Guardian": 2,
    "The New York Times": 2,
    "New York Times": 2,
    "The Washington Post": 2,
    "Washington Post": 2,
    "Forbes": 2,
    "Fortune": 2,
    "Business Insider": 2,
    "Axios": 2,
    "Politico": 2,
    "NPR": 2,
    "South China Morning Post": 2,
    "Nikkei Asia": 2,
    "The Telegraph": 2,
    "The Times": 2,
    "ABC News": 2,
    "CBS News": 2,
    "NBC News": 2,
    "Al Jazeera English": 2,
    "Foreign Policy": 2,
    "TheStreet": 2,
    "Morningstar": 2,
}

_STOP_WORDS = {
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "of", "for",
    "is", "are", "was", "were", "be", "been", "has", "have", "had", "its",
    "it", "this", "that", "as", "by", "with", "from", "but", "not", "new",
    "may", "says", "said", "after", "over", "up", "down", "into",
}

# Macro-finance relevance filter — drop articles with no signal words.
_FINANCE_WORDS_RE = re.compile(
    r'\b('
    r'yield|yields|bond|bonds|treasury|treasuries'
    r'|inflation|cpi|pce|pmi|gdp|deficit|surplus|stagflation|deflation|recession'
    r'|fomc|ecb|boj|boe|pboc|opec|cftc|imf'
    r'|crude|brent|wti|lng|bullion'
    r'|forex|dxy|vix'
    r'|monetary|fiscal|tariff|tariffs|sanction|sanctions|taper'
    r'|equities|commodity|commodities|palladium|platinum|aluminium'
    r'|stocks|shares|oil|gold|silver|copper|wheat|corn|soybeans'
    r'|dollar|euro|yen|yuan|peso|lira|ruble|franc'
    r'|nasdaq|nikkei|sensex|dax|ftse|kospi'
    r')\b',
    re.IGNORECASE,
)
_FINANCE_PHRASES_RE = re.compile(
    r'central bank|federal reserve|interest rate|rate hike|rate cut'
    r'|stock market|oil price|gold price|trade war|trade deal'
    r'|exchange rate|dollar index|market rally|sell.?off'
    r'|rate decision|balance sheet|quantitative easing'
    r'|s&p 500|hang seng|csi 300|russell 2000'
    r'|earnings report|earnings season|credit spread'
    r'|risk.?off|risk.?on',
    re.IGNORECASE,
)


_PRESS_RELEASE_RE = re.compile(
    r'(?:'
    r'\((?:nasdaq|nyse|tsx|otcqb|otcqx|otc):\s*\w+\)'  # inline stock tickers
    r'|™|®'                                               # trademark/registered symbols
    r'|announces?\s+pricing\s+of'
    r'|announces?\s+listing\s+on'
    r'|assay\s+results?'
    r'|underwritten\s+(?:public\s+)?offering'
    r'|board\s+chair(?:man|woman)?'
    r'|appoints?\s+\w+\s+as\s+(?:chief|president|vice|head|director|chair)'
    r'|names?\s+\w+\s+as\s+(?:chief|president|vice|head|director|chair)'
    r'|welcomes?\s+\w+\s+as\s+(?:new\s+)?(?:board|chair|chief|ceo|cfo|coo)'
    r')',
    re.IGNORECASE,
)


def _is_press_release(article: dict) -> bool:
    title = article.get("title") or ""
    return bool(_PRESS_RELEASE_RE.search(title))


def _is_finance_relevant(article: dict) -> bool:
    text = (article.get("title") or "") + " " + (article.get("description") or "")
    return bool(_FINANCE_WORDS_RE.search(text) or _FINANCE_PHRASES_RE.search(text))


# Maps asset labels to targeted search queries for dynamic headline fetching.
LABEL_TO_QUERY = {
    "Gold":          "gold price",
    "Silver":        "silver price",
    "Platinum":      "platinum price",
    "Palladium":     "palladium price",
    "Brent Crude":   "Brent crude oil",
    "WTI Crude":     "WTI crude oil",
    "Natural Gas":   "natural gas price",
    "Copper":        "copper price",
    "Iron Ore":      "iron ore price",
    "Aluminium":     "aluminium price",
    "EUR/USD":       "euro dollar forex",
    "GBP/USD":       "pound dollar forex",
    "USD/JPY":       "dollar yen forex",
    "USD/CHF":       "dollar franc forex",
    "USD/CNY":       "dollar yuan China",
    "USD/TRY":       "Turkey lira",
    "USD/BRL":       "Brazil real forex",
    "USD/MXN":       "Mexico peso forex",
    "USD/ZAR":       "South Africa rand",
    "USD/KRW":       "South Korea won forex",
    "AUD/USD":       "Australian dollar forex",
    "DXY":           "dollar index",
    "S&P 500":       "S&P 500",
    "Nasdaq 100":    "Nasdaq",
    "Dow Jones":     "Dow Jones",
    "Russell 2000":  "Russell 2000 small cap",
    "Euro Stoxx 50": "European stocks",
    "DAX":           "DAX Germany",
    "CAC 40":        "CAC France stocks",
    "FTSE 100":      "FTSE UK stocks",
    "Nikkei 225":    "Nikkei Japan",
    "Hang Seng":     "Hang Seng Hong Kong",
    "CSI 300":       "China stocks CSI 300",
    "VIX":           "VIX volatility",
    "Corn":          "corn price",
    "Wheat":         "wheat price",
    "Soybeans":      "soybeans price",
    "Coffee":        "coffee price",
    "Sugar":         "sugar price",
}


def _load_snapshot(today: str) -> dict:
    snapshot_path = os.path.join(
        os.path.dirname(__file__), "..", "content", "snapshots", f"{today}.json"
    )
    if not os.path.exists(snapshot_path):
        return {}
    with open(snapshot_path) as f:
        return json.load(f)


def _dynamic_queries(snapshot: dict, cap: int = 5) -> list[str]:
    assets = snapshot.get("assets", {})
    candidates = []
    for asset in assets.values():
        change_pct = asset.get("change_pct")
        if change_pct is not None and abs(change_pct) > 1.0:
            query = LABEL_TO_QUERY.get(asset.get("label", ""))
            if query:
                candidates.append((abs(change_pct), query))

    candidates.sort(key=lambda x: x[0], reverse=True)
    seen: set[str] = set()
    queries: list[str] = []
    for _, q in candidates:
        if q not in seen:
            seen.add(q)
            queries.append(q)
        if len(queries) >= cap:
            break
    return queries


def _fetch_articles(
    query: str, api_key: str, from_date: str, sources: str | None = None
) -> list[dict]:
    params: dict = {
        "q":        query,
        "from":     from_date,
        "sortBy":   "publishedAt",
        "language": "en",
        "pageSize": 20,
        "apiKey":   api_key,
    }
    if sources:
        params["domains"] = sources
    try:
        r = requests.get(NEWSAPI_URL, params=params, timeout=15, verify=certifi.where())
        r.raise_for_status()
        return r.json().get("articles", [])
    except Exception as exc:
        print(f"  [warn] NewsAPI query '{query}': {exc}", file=sys.stderr)
        return []


def _fetch_currents_articles(query: str, api_key: str, from_date: str) -> list[dict]:
    # Currents uses comma-separated keywords; convert "A OR B OR C" → "A, B, C"
    keywords = ", ".join(p.strip() for p in query.split(" OR "))
    try:
        r = requests.get(
            CURRENTS_URL,
            params={
                "keywords": keywords,
                "language": "en",
                "limit":    20,
                "apiKey":   api_key,
            },
            timeout=15,
            verify=certifi.where(),
        )
        r.raise_for_status()
        articles = []
        for item in r.json().get("news", []):
            url = item.get("url", "")
            domain = re.sub(r"^www\.", "", urlparse(url).netloc.lower())
            source_name = _DOMAIN_TO_SOURCE.get(domain, domain)
            # Normalise published timestamp to ISO-8601 for _score()
            pub = item.get("published", "").replace(" +0000", "+00:00")
            pub = pub[:10] + "T" + pub[11:] if len(pub) > 10 and pub[10] == " " else pub
            articles.append({
                "title":       item.get("title", ""),
                "description": item.get("description", ""),
                "url":         url,
                "source":      {"name": source_name},
                "publishedAt": pub,
            })
        return articles
    except Exception as exc:
        print(f"  [warn] Currents query '{query[:50]}': {exc}", file=sys.stderr)
        return []


def _score(article: dict, is_dynamic: bool, now: datetime) -> float:
    source = article.get("source", {}).get("name", "")
    tier = SOURCE_TIER.get(source, 1)

    pub_str = article.get("publishedAt", "")
    try:
        pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        age_hours = (now - pub).total_seconds() / 3600
        recency = 1 if age_hours <= 6 else (0 if age_hours <= 18 else -1)
    except Exception:
        recency = 0

    return tier + recency + (2 if is_dynamic else 0)


def _title_words(title: str) -> set[str]:
    words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
    return {w for w in words if w not in _STOP_WORDS}


def _is_near_duplicate(h1: dict, h2: dict, threshold: float = 0.6) -> bool:
    w1 = _title_words(h1["headline"])
    w2 = _title_words(h2["headline"])
    if not w1 or not w2:
        return False
    return len(w1 & w2) / min(len(w1), len(w2)) >= threshold


def fetch_news(today: str, newsapi_key: str, currents_key: str | None = None) -> list[dict]:
    now = datetime.now(timezone.utc)
    snapshot = _load_snapshot(today)
    dynamic_queries = _dynamic_queries(snapshot)
    dynamic_set = set(dynamic_queries)
    from_date = (date.fromisoformat(today) - timedelta(days=1)).isoformat()

    # Process dynamic queries first so their articles are tagged "dynamic"
    # before static queries can claim the same URLs.
    ordered_queries: list[tuple[str, str]] = (
        [(q, "dynamic") for q in dynamic_queries] +
        [(q, QUERY_BUCKETS[q]) for q in QUERY_BUCKETS]
    )

    seen_urls: set[str] = set()
    candidates: list[tuple[float, dict, str]] = []  # (score, article, bucket)

    def _ingest(article: dict, bucket: str, is_dynamic: bool) -> None:
        if not _is_finance_relevant(article) or _is_press_release(article):
            return
        url = article.get("url", "")
        if not url or url in seen_urls:
            return
        seen_urls.add(url)
        candidates.append((_score(article, is_dynamic, now), article, bucket))

    # NewsAPI — quality domains filter applied at API level (24h delay on free plan)
    for query, bucket in ordered_queries:
        for article in _fetch_articles(query, newsapi_key, from_date, sources=_QUALITY_DOMAINS):
            _ingest(article, bucket, query in dynamic_set)

    # Currents API — real-time; domain quality filter applied post-fetch since
    # the API has no equivalent of NewsAPI's domains parameter.
    if currents_key:
        for query, bucket in ordered_queries:
            for article in _fetch_currents_articles(query, currents_key, from_date):
                src = article.get("source", {}).get("name", "")
                if SOURCE_TIER.get(src, 0) < 2:
                    continue
                _ingest(article, bucket, query in dynamic_set)

    # Sort by score descending, dedup near-identical titles, apply global cap.
    candidates.sort(key=lambda x: x[0], reverse=True)

    final: list[dict] = []
    for _, article, bucket in candidates:
        if len(final) >= GLOBAL_HEADLINE_CAP:
            break
        h = {
            "headline":    article.get("title", ""),
            "source":      article.get("source", {}).get("name", "Unknown"),
            "description": article.get("description", ""),
            "url":         article.get("url", ""),
            "publishedAt": article.get("publishedAt", ""),
            "bucket":      bucket,
        }
        if not h["headline"]:
            continue
        if any(_is_near_duplicate(h, existing) for existing in final):
            continue
        final.append(h)

    final.sort(key=lambda h: h["publishedAt"], reverse=True)
    return final


def main():
    newsapi_key   = os.environ.get("NEWSAPI_KEY", "")
    currents_key  = os.environ.get("CURRENTAPI_KEY", "")
    if not newsapi_key and not currents_key:
        print("Error: NEWSAPI_KEY or CURRENTAPI_KEY must be set", file=sys.stderr)
        sys.exit(1)

    today    = date.today().isoformat()
    news_dir = os.path.join(os.path.dirname(__file__), "..", "content", "news")
    os.makedirs(news_dir, exist_ok=True)
    out_path = os.path.join(news_dir, f"{today}.json")

    print(f"\nDownstream news fetch — {today}")
    print("=" * 52)
    print(f"  NewsAPI  : {'active (24h delay on free plan)' if newsapi_key else 'not configured'}")
    print(f"  Currents : {'active (real-time)' if currents_key else 'not configured'}")

    snapshot = _load_snapshot(today)
    dynamic  = _dynamic_queries(snapshot)
    print(f"  Static queries : {len(QUERY_BUCKETS)}")
    if dynamic:
        print(f"  Dynamic queries: {len(dynamic)} — {dynamic}")

    headlines = fetch_news(today, newsapi_key, currents_key)

    bucket_counts: dict[str, int] = {}
    for h in headlines:
        b = h.get("bucket", "?")
        bucket_counts[b] = bucket_counts.get(b, 0) + 1
    print(f"  Headlines      : {len(headlines)}")
    for bucket, count in sorted(bucket_counts.items()):
        print(f"    {bucket:<22} {count}")
    print("=" * 52)

    payload = {"date": today, "headlines": headlines}
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nNews     → {out_path}")
    return out_path


if __name__ == "__main__":
    main()
