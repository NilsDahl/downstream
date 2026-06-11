"""
generate_draft.py — reads a market snapshot JSON and calls Claude to produce
a macro implication chain analysis in markdown.

Output: /content/drafts/YYYY-MM-DD.md
"""

import json
import os
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
You are the author of Downstream, a daily macro-finance brief for finance \
students and young professionals. Your job: identify the primary driver in \
today's market moves and trace its implication chain through related assets.

CRITICAL DATA RULE: Every number you cite must be copied verbatim from \
the market snapshot provided. Do not round, re-derive, or approximate any \
price, yield, or percentage change. If a figure is not in the snapshot, do \
not state it.

Writing rules:
- Lead with the PRIMARY DRIVER: the largest, most anomalous, or most \
  explanatory move. Name it precisely.
- Macro relevance hierarchy: sovereign yields, central bank rates, equity \
  indices, oil, gold, and DXY have broad macro chain implications and should \
  be preferred as primary drivers. Single-commodity agricultural moves \
  (cotton, coffee, sugar, wheat) are typically idiosyncratic supply/demand \
  events — do not make them the primary driver unless they are corroborated \
  by moves in at least two other related assets (e.g. all grains moving \
  together, or a food-inflation reading). If an agricultural commodity shows \
  a large isolated move not corroborated elsewhere, note it briefly as a \
  footnote to the chain rather than leading with it.
- Build the chain outward from that driver, node by node. Each node must \
  name the mechanism, not just the direction. "Higher oil → inflation \
  expectations re-price → breakevens widen" not "oil went up so bonds fell."
- If two moves contradict each other, name the tension explicitly. Do not \
  paper over it.
- 4–6 nodes. 2–4 sentences per node. No padding.
- Close with "What to watch": 2–3 specific, falsifiable signals. Name the \
  instrument, the level, or the event — not vague market commentary.
- Tone: analytical, precise, no filler.
- Forbidden phrases: "it remains to be seen", "investors will be watching", \
  "in this environment", "navigating uncertainty", "amid", "backdrop".

Output format — use exactly this structure:

**The driver:** [one sentence with the exact figure from the snapshot]

**The chain:**

**[Node label]:** [2–4 sentences explaining the mechanism]

**[Node label]:** [2–4 sentences]

[4–6 nodes total]

**What to watch:** [2–3 sentences, specific and falsifiable]\
"""


def build_user_prompt(snapshot: dict) -> str:
    summary       = build_market_summary(snapshot)
    snapshot_date = snapshot.get("date", date.today().isoformat())
    return (
        f"Date: {snapshot_date}\n\n"
        f"Market snapshot — previous session closes, all changes vs prior session:\n\n"
        f"{summary}\n\n"
        f"Write today's Downstream implication chain analysis. "
        f"Use only the exact figures above — do not invent or approximate any number."
    )


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def generate_draft(snapshot_path: str) -> str:
    with open(snapshot_path) as f:
        snapshot = json.load(f)

    snapshot_date = snapshot.get("date", date.today().isoformat())
    client        = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_prompt = build_user_prompt(snapshot)

    print(f"Calling {MODEL} …")
    message = client.messages.create(
        model=MODEL,
        max_tokens=1400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    draft_text = message.content[0].text
    frontmatter = f"---\ndate: {snapshot_date}\nmodel: {MODEL}\n---\n\n"
    full_draft  = frontmatter + draft_text

    draft_dir = os.path.join(
        os.path.dirname(__file__), "..", "content", "drafts"
    )
    os.makedirs(draft_dir, exist_ok=True)
    out_path = os.path.join(draft_dir, f"{snapshot_date}.md")

    with open(out_path, "w") as f:
        f.write(full_draft)

    print(f"Draft written → {out_path}")
    print(f"Tokens — input: {message.usage.input_tokens}, output: {message.usage.output_tokens}")
    return out_path


def main():
    if len(sys.argv) > 1:
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
