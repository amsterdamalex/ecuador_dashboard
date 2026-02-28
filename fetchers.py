"""
Ecuador OSINT Dashboard — Data fetching (RSS, NewsAPI, ACLED).

Depends on Streamlit for @st.cache_data. All network I/O isolated here.
"""

import re
from datetime import datetime, timedelta

import feedparser
import pandas as pd
import requests
import streamlit as st


@st.cache_data(ttl=1800)
def fetch_rss(url: str, days_back: int) -> list[dict]:
    cutoff = datetime.now() - timedelta(days=days_back)
    try:
        # feedparser.parse(url) uses urllib with NO timeout — can hang forever.
        # Fetch the raw XML ourselves with a strict timeout, then parse the bytes.
        resp = requests.get(url, timeout=10)
        feed = feedparser.parse(resp.content)
    except Exception:
        return []
    entries = []
    for entry in feed.entries[:40]:
        pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        pub_date = datetime(*pub_parsed[:6]) if pub_parsed else None
        if pub_date and pub_date < cutoff:
            continue
        entries.append({
            "Title":     entry.get("title", "(no title)"),
            "Source":    feed.feed.get("title", url),
            "Link":      entry.get("link", ""),
            "Published": pub_date.strftime("%Y-%m-%d %H:%M") if pub_date else "Unknown",
            "Summary":   re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:500],
            "_pub_dt":   pub_date or datetime.min,
        })
    return entries


@st.cache_data(ttl=3600)
def fetch_newsapi(api_key: str, keywords: list[str], days_back: int) -> list[dict]:
    query = " OR ".join(keywords[:10])
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={requests.utils.quote(query)}"
        f"&language=es&from={from_date}&sortBy=publishedAt&pageSize=30"
        f"&apiKey={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10).json()
        if resp.get("status") != "ok":
            return []
        results = []
        for a in resp.get("articles", []):
            pub_str = a.get("publishedAt", "")
            try:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pub_dt = datetime.min
            results.append({
                "Title":     a.get("title") or "(no title)",
                "Source":    a["source"]["name"],
                "Link":      a.get("url", ""),
                "Published": pub_dt.strftime("%Y-%m-%d %H:%M") if pub_dt != datetime.min else pub_str[:10],
                "Summary":   a.get("description") or "",
                "_pub_dt":   pub_dt,
            })
        return results
    except Exception:
        return []


@st.cache_data(ttl=3600)
def fetch_acled(email: str, key: str, days_back: int) -> pd.DataFrame:
    """Fetch Ecuador conflict events from ACLED API."""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = (
        "https://api.acleddata.com/acled/read?"
        f"key={key}&email={email}"
        "&country=Ecuador"
        f"&event_date={from_date}|{datetime.now().strftime('%Y-%m-%d')}"
        "&event_date_where=BETWEEN"
        "&limit=500"
        "&fields=event_date|event_type|sub_event_type|actor1|location|latitude|longitude|fatalities|notes"
    )
    try:
        resp = requests.get(url, timeout=15).json()
        data = resp.get("data", [])
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()
