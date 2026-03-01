"""
Ecuador OSINT Dashboard — Data fetching (RSS, NewsAPI, ACLED).

Depends on Streamlit for @st.cache_data. All network I/O isolated here.
"""

import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import feedparser
import pandas as pd
import requests
import streamlit as st

# Global safety net: any socket that doesn't set its own timeout
# will bail after 10s. Covers DNS resolution hangs that
# requests' timeout=(connect, read) does NOT cover.
socket.setdefaulttimeout(10)


def _fetch_single_rss(url: str, days_back: int) -> list[dict]:
    """Fetch one RSS feed. No Streamlit dependency — safe to call from threads."""
    cutoff = datetime.now() - timedelta(days=days_back)
    try:
        resp = requests.get(url, timeout=(2, 5))
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


@st.cache_data(ttl=1800)
def fetch_all_rss(source_urls: dict[str, str], days_back: int) -> tuple[list[dict], list[str]]:
    """Fetch all RSS feeds in parallel. Cached on the main thread."""
    all_news: list[dict] = []
    errors: list[str] = []

    if not source_urls:
        return all_news, errors

    def _fetch_one(name: str, url: str):
        try:
            return name, _fetch_single_rss(url, days_back), None
        except Exception as e:
            return name, None, f"{name}: {e}"

    pool = ThreadPoolExecutor(max_workers=min(len(source_urls), 6))
    futures = {pool.submit(_fetch_one, name, url): name for name, url in source_urls.items()}
    try:
        for fut in as_completed(futures, timeout=15):
            try:
                name, results, err = fut.result(timeout=5)
            except Exception:
                errors.append(f"{futures[fut]}: timed out")
                continue
            if err:
                errors.append(err)
            elif results:
                all_news.extend(results)
    except Exception:
        errors.append("Some feeds timed out")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    return all_news, errors


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
        resp = requests.get(url, timeout=8).json()
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
                "Source":    a.get("source", {}).get("name", "NewsAPI"),
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
        resp = requests.get(url, timeout=10).json()
        data = resp.get("data", [])
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()
