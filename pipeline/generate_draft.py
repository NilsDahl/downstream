"""
generate_draft.py — reads a market snapshot JSON and calls Claude to produce
a macro implication chain analysis in markdown.

Output: /content/drafts/YYYY-MM-DD.md
"""

import json
import os
import re
import sys
from datetime import date

import anthropic

MODEL = "claude-sonnet-4-6"

# ─────────────────────────────────────────────────────────────
# Snapshot → structured text for the prompt
# ─────────────────────────────────────────────────────────────

# Only send a curated subset to the model — the full 85-asset universe
# is too noisy. Focus on macro-relevant instruments.
PROMPT_ASSET_GROUPS = [
    ("US YIELD CURVE",       "rates",       "us"),
    ("EUROZONE YIELD CURVE", "rates",       "eurozone"),
    ("SWEDEN RATES",         "rates",       "sweden"),
    ("UK RATES",             "rates",       "uk"),
    ("FX — MAJORS",          "fx",          "majors"),
    ("FX — COMMODITY CCY",   "fx",          "commodity"),
    ("FX — EM SELECT",       "fx",          "em"),
    ("FX — CROSSES",         "fx",          "cross"),
    ("DOLLAR INDEX",         "fx",          "index"),
    ("EQUITIES — US",        "equities",    "us"),
    ("EQUITIES — EUROPE",    "equities",    "europe"),
    ("EQUITIES — ASIA",      "equities",    "asia"),
    ("VOLATILITY",           "equities",    "volatility"),
    ("ENERGY",               "commodities", "energy"),
    ("PRECIOUS METALS",      "commodities", "precious_metals"),
    ("INDUSTRIAL METALS",    "commodities", "industrial_metals"),
    ("AGRICULTURE",          "commodities", "agriculture"),
]

# EM FX — only show the most macro-relevant pairs
EM_ALLOWLIST = {"usdcny", "usdbrl", "usdmxn", "usdzar", "usdtry"}


def _fmt_rate(asset: dict) -> str:
    label = asset["label"]
    level = asset.get("level")
    chg   = asset.get("change_bps")
    if level is None:
        return None
    sign = "+" if isinstance(chg, (int, float)) and chg > 0 else ""
    chg_str = f"{sign}{chg:.1f} bps" if chg is not None else "n/a"
    return f"  {label}: {level:.4f}%  ({chg_str})"


def _fmt_price(key: str, asset: dict) -> str:
    label = asset["label"]
    close = asset.get("close")
    chg   = asset.get("change_pct")
    if close is None:
        return None
    sign = "+" if isinstance(chg, (int, float)) and chg > 0 else ""
    chg_str = f"{sign}{chg:.2f}%" if chg is not None else "n/a"
    return f"  {label}: {close:.4f}  ({chg_str})"


def build_market_summary(snapshot: dict) -> str:
    assets = snapshot.get("assets", {})
    sections = []

    for group_label, category, sub_category in PROMPT_ASSET_GROUPS:
        lines = []
        for key, asset in assets.items():
            if asset.get("category") != category:
                continue
            if asset.get("sub_category") != sub_category:
                continue
            # Filter EM to allowlist only
            if sub_category == "em" and key not in EM_ALLOWLIST:
                continue
            if asset.get("level") is not None:
                line = _fmt_rate(asset)
            else:
                line = _fmt_price(key, asset)
            if line:
                lines.append(line)
        if lines:
            sections.append(f"{group_label}\n" + "\n".join(lines))

    return "\n\n".join(sections)


# ─────────────────────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are the author of Downstream, a daily macro-finance brief for curious, \
intelligent readers — people who follow the news but don't trade markets for \
a living. Your job: identify the primary driver(s) of today's macro narrative \
and trace implication chain(s) through related assets.

The primary driver is whatever best explains the day — it may be a news \
catalyst, a market move, or both together. A significant news event that \
caused a modest market move takes priority over a larger but unrelated price \
swing. Read the news and the snapshot as co-equal inputs: together they tell \
you what the day is actually about.

CRITICAL DATA RULE: Every number you cite must be copied verbatim from \
the market snapshot provided. Do not round, re-derive, or approximate any \
price, yield, or percentage change. If a figure is not in the snapshot, do \
not state it.

HOW MANY CHAINS:
- A chain must have ONE external driver: a single news event, data release, \
  or policy signal that is sufficient on its own to explain the moves in that \
  chain. If you find yourself writing "and also..." or weaving in a second \
  unrelated catalyst, split into a separate chain.
- Use as many chains as there are distinct drivers — typically 2–3 per session. \
  Do not collapse distinct drivers into one chain to achieve surface unity.
- ONE chain is correct only when a single event genuinely explains all the \
  major cross-asset moves that day (rare). TWO or THREE chains is the normal \
  case on most macro days.
- When in doubt, split — a clean two-chain session is more useful than a \
  bloated one-chain session.

Writing rules:
- Lead each chain with its PRIMARY DRIVER: the single catalyst — news event, \
  policy signal, or market move — that most coherently explains that chain's \
  pattern across assets.
- If a news catalyst is the driver, anchor it to the market data: show which \
  assets moved in response and by how much. If a market move is the driver, \
  anchor it to the news: name the mechanism behind it.
- Macro relevance hierarchy: sovereign yields, central bank rates, equity \
  indices, oil, gold, and DXY have broad macro chain implications and should \
  be preferred as primary drivers. Single-commodity agricultural moves \
  (cotton, coffee, sugar, wheat) are typically idiosyncratic supply/demand \
  events — do not make them the primary driver unless they are corroborated \
  by moves in at least two other related assets. If an agricultural commodity \
  shows a large isolated move not corroborated elsewhere, note it briefly as \
  a footnote to the chain rather than leading with it.
- Build each chain as a strict transitive sequence: each step must be causally \
  downstream of the step before it, not merely downstream of the original \
  driver. The test: if you remove any middle step, does the next step stop \
  making logical sense? If the next step still makes sense, those steps are \
  parallel observations — merge or cut them. Every step after the first must \
  open with an explicit causal connector: "Because [X]...", \
  "This repricing then...", "With dollar demand surging...". Node labels must \
  name the transmission mechanism, not the asset class: \
  "Higher US real yields attract dollar-denominated capital" is correct. \
  "The dollar machine re-ignites" or "Gold under pressure" are not — they \
  name outcomes, not mechanisms.
- When a move contradicts what the chain would predict, flag it in one sentence \
  at the end of the node where the contradiction first appears: \
  "Tension: [asset] is moving opposite to the chain because [mechanism]." \
  Do not give contradictions their own full node — if a contradiction is large \
  enough to need its own explanation, it belongs in a separate chain with its \
  own driver.
- 3–5 steps per chain. 2–4 sentences per step. Fewer, tighter steps are \
  better than more loosely connected ones. No padding.
- Close each chain with "What to watch": 2–3 specific, falsifiable signals. \
  Name the instrument, the level, or the event — not vague market commentary.
- Define jargon on first use with a brief parenthetical — e.g., \
  "basis points (bps, hundredths of a percentage point)", \
  "the yield curve (the line connecting short- to long-term interest rates)", \
  "the carry trade (borrowing cheaply in one currency to invest in a \
  higher-yielding one)". Do not define the same term twice.
- For each mechanism in the chain, lead with what it means in plain terms \
  before stating the technical label. "When oil prices fall, everyday goods \
  get cheaper to produce and ship — this reduces inflation expectations, which \
  means bond investors demand less compensation for future price rises, so \
  yields fall" is better than "oil down → breakevens compress → yields fall."
- Analogies are encouraged when they are accurate. A rate-relief rally in \
  bonds is like a traffic jam clearing — once pressure lifts, everyone \
  accelerates at once.
- Tone: clear, precise, curious. Write as if explaining to a smart friend \
  who reads the Economist but doesn't trade markets. Keep all numbers exact. \
  Cut filler, not clarity.
- Forbidden phrases: "it remains to be seen", "investors will be watching", \
  "in this environment", "navigating uncertainty", "amid", "backdrop".

Output format — for a SINGLE chain:

## Chain 1: [Short descriptive title, 4–7 words]

**The driver:** [one sentence naming the catalyst and its exact figure or source]

**The chain:**

**[Node label — name the mechanism, not the asset class]:** [2–4 sentences explaining the mechanism. Steps after the first must open with a causal connector.]

**[Node label]:** [2–4 sentences]

[3–5 steps total]

**What to watch:** [2–3 sentences, specific and falsifiable]

Output format — for MULTIPLE chains (repeat the block):

## Chain 1: [Title]

**The driver:** ...

**The chain:**

...

**What to watch:** ...

## Chain 2: [Title]

**The driver:** ...

**The chain:**

...

**What to watch:** ...\
"""

NEWS_SUMMARY_SYSTEM = """\
You are summarizing financial market news for a daily macro brief. \
Write 8–12 bullet points covering the most important stories from today's \
headlines. Each bullet: lead with **bold key fact** (asset name, move \
magnitude, institution, or event), then one sentence of context explaining \
why it matters macroeconomically. Prioritize systemic significance over \
novelty. Tone: terse, precise. No filler, no opinions, no forbidden phrases \
(amid, backdrop, navigating uncertainty). \
Output ONLY the bullet list — no title, no heading, no preamble.\
"""


def load_news_context(snapshot_date: str) -> str | None:
    news_path = os.path.join(
        os.path.dirname(__file__), "..", "content", "news", f"{snapshot_date}.json"
    )
    if not os.path.exists(news_path):
        return None
    with open(news_path) as f:
        data = json.load(f)
    headlines = data.get("headlines", [])
    if not headlines:
        return None
    lines = []
    for h in headlines:
        source = h.get("source", "Unknown")
        headline = h.get("headline", "").strip()
        body = (h.get("body") or "").strip()
        description = (h.get("description") or "").strip()
        bucket = h.get("bucket", "")
        tag = f"[{bucket}] " if bucket else ""
        content = body if body else description
        if content:
            lines.append(f"- {tag}[{source}] {headline} — {content}")
        else:
            lines.append(f"- {tag}[{source}] {headline}")
    return "\n".join(lines)


def build_user_prompt(snapshot: dict) -> str:
    summary       = build_market_summary(snapshot)
    snapshot_date = snapshot.get("date", date.today().isoformat())
    news_context  = load_news_context(snapshot_date)

    prompt = f"Date: {snapshot_date}\n\n"

    if news_context:
        prompt += (
            f"News headlines — last 24 hours:\n{news_context}\n\n"
        )

    prompt += (
        "Data timing — critical for correct analysis:\n"
        "- FX, equities, commodities: T (today's session closes and changes).\n"
        "- ALL yield curves and reference rates (SOFR, €STR, SWESTR, SONIA, "
        "US Treasuries, Bunds, Gilts, JGBs, etc.): T−1 (prior session). "
        "Central banks publish rates with a one-day lag; overnight reference rates "
        "are backward-looking by design and cannot be real-time. "
        "The bps changes shown for rates are T−2 → T−1, not today's moves.\n\n"
        "Use rates as the prior-session backdrop that sets the context. "
        "Do not say rates 'moved today' or describe rate changes as today's events. "
        "Instead frame them as: 'going into today, yields were at X' or "
        "'the prior session saw yields rise/fall, against which today's equity/FX moves...'\n\n"
        f"Market snapshot:\n\n"
        f"{summary}\n\n"
    )

    if news_context:
        prompt += (
            "Use both inputs together to decide what today is about. The primary driver\n"
            "may be a news catalyst, a market move, or their intersection — whichever\n"
            "most coherently explains the pattern across assets. Do not treat news as\n"
            "a footnote to the data; treat it as a co-equal input in choosing the chain.\n\n"
        )

    prompt += (
        "Write today's Downstream implication chain analysis. "
        "Use only the exact figures from the snapshot — do not invent or approximate any number."
    )
    return prompt


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def generate_news_summary(snapshot_date: str, client: anthropic.Anthropic) -> str | None:
    news_context = load_news_context(snapshot_date)
    if not news_context:
        return None

    print(f"Generating news summary …")
    msg = client.messages.create(
        model=MODEL,
        max_tokens=900,
        system=NEWS_SUMMARY_SYSTEM,
        messages=[{"role": "user", "content": f"Date: {snapshot_date}\n\nHeadlines:\n{news_context}"}],
    )
    print(f"News summary tokens — input: {msg.usage.input_tokens}, output: {msg.usage.output_tokens}")
    return msg.content[0].text.strip()


def generate_draft(snapshot_path: str) -> str:
    with open(snapshot_path) as f:
        snapshot = json.load(f)

    snapshot_date = snapshot.get("date", date.today().isoformat())
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set", file=sys.stderr)
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    user_prompt = build_user_prompt(snapshot)

    print(f"Calling {MODEL} for implication chain(s) …")
    message = client.messages.create(
        model=MODEL,
        max_tokens=2400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    # Strip any leading title / divider Claude adds before the first ## Chain section
    raw = message.content[0].text
    chain_start = re.search(r'^## Chain \d+:', raw, re.MULTILINE)
    chain_text = raw[chain_start.start():].strip() if chain_start else raw.strip()
    print(f"Chain tokens — input: {message.usage.input_tokens}, output: {message.usage.output_tokens}")

    news_summary = generate_news_summary(snapshot_date, client)

    body_parts = []
    if news_summary:
        body_parts.append(f"## News Summary\n\n{news_summary}")
    body_parts.append(chain_text)

    frontmatter = f"---\ndate: {snapshot_date}\nmodel: {MODEL}\n---\n\n"
    full_draft  = frontmatter + "\n\n".join(body_parts)

    draft_dir = os.path.join(
        os.path.dirname(__file__), "..", "content", "drafts"
    )
    os.makedirs(draft_dir, exist_ok=True)
    out_path = os.path.join(draft_dir, f"{snapshot_date}.md")

    with open(out_path, "w") as f:
        f.write(full_draft)

    print(f"Draft written → {out_path}")
    return out_path


def main():
    if "--date" in sys.argv:
        d             = sys.argv[sys.argv.index("--date") + 1]
        snapshot_path = os.path.join(
            os.path.dirname(__file__), "..", "content", "snapshots", f"{d}.json"
        )
    elif len(sys.argv) > 1:
        snapshot_path = sys.argv[1]
    else:
        today         = date.today().isoformat()
        snapshot_path = os.path.join(
            os.path.dirname(__file__), "..", "content", "snapshots", f"{today}.json"
        )

    if not os.path.exists(snapshot_path):
        print(f"Error: snapshot not found at {snapshot_path}", file=sys.stderr)
        sys.exit(1)

    generate_draft(snapshot_path)


if __name__ == "__main__":
    main()
