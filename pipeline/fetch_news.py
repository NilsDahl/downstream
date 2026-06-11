"""
fetch_news.py — fetches relevant news headlines from NewsAPI.

Runs after fetch_data.py as part of the daily pipeline.
Requires NEWSAPI_KEY in the environment.

Output: /content/news/YYYY-MM-DD.json
"""

import json
import os
import sys
from datetime import date, timedelta

import certifi
import requests

NEWSAPI_URL = "https://newsapi.org/v2/everything"

STATIC_QUERIES = [
    "Federal Reserve OR Fed rate",
    "ECB OR European Central Bank",
    "oil price OR crude OR OPEC",
    "inflation OR CPI",
    "China economy OR PBOC",
    "Treasury bonds OR yield curve",
]

# Maps asset labels to targeted search queries for dynamic headline fetching
LABEL_TO_QUERY = {
    "Gold":              "gold price",
    "Silver":            "silver price",
    "Platinum":          "platinum price",
    "Palladium":         "palladium price",
    "Brent Crude":       "Brent crude oil",
    "WTI Crude":         "WTI crude oil",
    "Natural Gas":       "natural gas price",
    "Copper":            "copper price",
    "Iron Ore":          "iron ore price",
    "Aluminium":         "aluminium price",
    "EUR/USD":           "euro dollar forex",
    "GBP/USD":           "pound dollar forex",
    "USD/JPY":           "dollar yen forex",
    "USD/CHF":           "dollar franc forex",
    "USD/CNY":           "dollar yuan China",
    "USD/TRY":           "Turkey lira",
    "USD/BRL":           "Brazil real forex",
    "USD/MXN":           "Mexico peso forex",
    "USD/ZAR":           "South Africa rand",
    "USD/KRW":           "South Korea won forex",
    "AUD/USD":           "Australian dollar forex",
    "DXY":               "dollar index",
    "S&P 500":           "S&P 500",
    "Nasdaq 100":        "Nasdaq",
    "Dow Jones":         "Dow Jones",
    "Russell 2000":      "Russell 2000 small cap",
    "Euro Stoxx 50":     "European stocks",
    "DAX":               "DAX Germany",
    "CAC 40":            "CAC France stocks",
    "FTSE 100":          "FTSE UK stocks",
    "Nikkei 225":        "Nikkei Japan",
    "Hang Seng":         "Hang Seng Hong Kong",
    "CSI 300":           "China stocks CSI 300",
    "VIX":               "VIX volatility",
    "Corn":              "corn price",
    "Wheat":             "wheat price",
    "Soybeans":          "soybeans price",
    "Coffee":            "coffee price",
    "Sugar":             "sugar price",
}


def _asset_to_query(label: str) -> str | None:
    return LABEL_TO_QUERY.get(label)


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
            query = _asset_to_query(asset.get("label", ""))
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


def _fetch_articles(query: str, api_key: str, from_date: str) -> list[dict]:
    try:
        r = requests.get(
            NEWSAPI_URL,
            params={
                "q":        query,
                "from":     from_date,
                "sortBy":   "publishedAt",
                "language": "en",
                "pageSize": 10,
                "apiKey":   api_key,
            },
            timeout=15,
            verify=certifi.where(),
        )
        r.raise_for_status()
        return r.json().get("articles", [])
    except Exception as exc:
        print(f"  [warn] NewsAPI query '{query}': {exc}", file=sys.stderr)
        return []


def fetch_news(today: str, api_key: str) -> list[dict]:
    snapshot    = _load_snapshot(today)
    dynamic     = _dynamic_queries(snapshot)
    all_queries = STATIC_QUERIES + dynamic
    from_date   = (date.fromisoformat(today) - timedelta(days=1)).isoformat()

    seen_urls: set[str] = set()
    headlines: list[dict] = []

    for query in all_queries:
        for article in _fetch_articles(query, api_key, from_date):
            url = article.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            headlines.append({
                "headline":    article.get("title", ""),
                "source":      article.get("source", {}).get("name", "Unknown"),
                "description": article.get("description", ""),
                "url":         url,
                "publishedAt": article.get("publishedAt", ""),
            })

    headlines.sort(key=lambda h: h["publishedAt"], reverse=True)
    return headlines[:20]


def main():
    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        print("Error: NEWSAPI_KEY not set", file=sys.stderr)
        sys.exit(1)

    today    = date.today().isoformat()
    news_dir = os.path.join(os.path.dirname(__file__), "..", "content", "news")
    os.makedirs(news_dir, exist_ok=True)
    out_path = os.path.join(news_dir, f"{today}.json")

    print(f"\nDownstream news fetch — {today}")
    print("=" * 52)

    snapshot = _load_snapshot(today)
    dynamic  = _dynamic_queries(snapshot)
    print(f"  Static queries : {len(STATIC_QUERIES)}")
    if dynamic:
        print(f"  Dynamic queries: {len(dynamic)} — {dynamic}")

    headlines = fetch_news(today, api_key)
    print(f"  Headlines      : {len(headlines)}")
    print("=" * 52)

    payload = {"date": today, "headlines": headlines}
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nNews     → {out_path}")
    return out_path


if __name__ == "__main__":
    main()
