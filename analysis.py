"""
Ecuador OSINT Dashboard — Pure analysis functions.

No Streamlit dependency. Only stdlib + textblob + spaCy (optional).
"""

import re

import pandas as pd
from textblob import TextBlob

from config import (
    HIGH_SEVERITY,
    KEYWORD_THEMES,
    LOCATION_COORDS,
    MEDIUM_SEVERITY,
)


def compute_severity(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    if any(w in text for w in HIGH_SEVERITY):
        return "🔴 High"
    if any(w in text for w in MEDIUM_SEVERITY):
        return "🟡 Medium"
    return "🟢 Low"


def compute_sentiment(text: str) -> tuple[str, float]:
    try:
        blob = TextBlob(text)
        score = blob.sentiment.polarity
        if score < -0.15:
            label = "Negative"
        elif score > 0.15:
            label = "Positive"
        else:
            label = "Neutral"
        return label, round(score, 3)
    except Exception:
        return "Neutral", 0.0


def extract_entities(text: str, nlp) -> dict[str, list[str]]:
    if nlp is None:
        return {}
    try:
        doc = nlp(text[:1000])
        entities: dict[str, list[str]] = {}
        for ent in doc.ents:
            entities.setdefault(ent.label_, []).append(ent.text)
        return entities
    except Exception:
        return {}


def tag_themes(title: str, summary: str) -> list[str]:
    text = (title + " " + summary).lower()
    tags = []
    for theme, kws in KEYWORD_THEMES.items():
        if any(kw.lower() in text for kw in kws):
            tags.append(theme)
    return tags


def keyword_match(row: dict, kws: list[str]) -> bool:
    haystack = (row["Title"] + " " + row["Summary"]).lower()
    return not kws or any(kw in haystack for kw in kws)


def highlight(text: str, kws: list[str]) -> str:
    for kw in kws:
        text = re.sub(f"({re.escape(kw)})", r"**\1**", text, flags=re.IGNORECASE)
    return text


def detect_locations(text: str) -> list[tuple[str, float, float]]:
    found = []
    tl = text.lower()
    for loc, coords in LOCATION_COORDS.items():
        if loc in tl:
            found.append((loc.title(), coords[0], coords[1]))
    return found


def generate_briefing(df: pd.DataFrame, acled_df: pd.DataFrame, days_back: int) -> str:
    from datetime import datetime

    now = datetime.now().strftime("%d %B %Y, %H:%M UTC")
    high = df[df["Severity"] == "🔴 High"]
    top_sources = df["Source"].value_counts().head(3).index.tolist()
    themes = df["Themes"].explode().value_counts().head(3).index.tolist() if "Themes" in df else []

    acled_summary = ""
    if not acled_df.empty and "fatalities" in acled_df.columns:
        total_events = len(acled_df)
        total_fatalities = pd.to_numeric(acled_df["fatalities"], errors="coerce").sum()
        acled_summary = (
            f"\n**ACLED Conflict Data ({len(acled_df)} events):** "
            f"{total_events} documented incidents, "
            f"{int(total_fatalities)} reported fatalities in the period.\n"
        )

    brief = f"""# ECUADOR SITUATION REPORT
**Generated:** {now}
**Period covered:** Last {days_back} days
**Classification:** UNCLASSIFIED — PUBLIC SOURCES ONLY

---

## EXECUTIVE SUMMARY

This report covers open-source monitoring of Ecuador over the past {days_back} days.
A total of **{len(df)} articles** were identified across {df['Source'].nunique()} sources.
Of these, **{len(high)} articles** were assessed as HIGH severity.
{acled_summary}
Leading themes identified: {', '.join(themes) if themes else 'N/A'}.
Primary sources: {', '.join(top_sources)}.

---

## HIGH SEVERITY INCIDENTS

"""
    for _, row in high.head(8).iterrows():
        brief += f"- **{row['Published'][:10]}** | {row['Source']}\n  {row['Title']}\n  {row['Link']}\n\n"

    brief += """---

## METHODOLOGY

All data sourced from publicly available RSS feeds, NewsAPI.org, and ACLED (Armed Conflict Location & Event Data Project).
No social media scraping. No classified or proprietary sources.
Sentiment analysis via TextBlob. Entity extraction via spaCy es_core_news_sm.
For NGO/research use only. Verify all incidents through primary sources before operational use.

---
*Ecuador OSINT Dashboard v3.0 — Human Rights Edition*
"""
    return brief
