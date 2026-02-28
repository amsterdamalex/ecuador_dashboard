"""
Ecuador Public OSINT Dashboard v2.0
100% Legal & Ethical — Public RSS + NewsAPI only.
No social-media scraping. For research/education only.

Install:  pip install streamlit pandas feedparser requests
Run:      streamlit run ecuador_osint_v2.py
"""

import re
from datetime import datetime, timedelta

import feedparser
import pandas as pd
import requests
import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ecuador OSINT Dashboard v2.0",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🇪🇨 Ecuador Public OSINT Dashboard v2.0")
st.markdown(
    "**100% Legal & Ethical** — Public RSS + NewsAPI only. "
    "No social-media scraping. No MILINT. For research/education only."
)

# ── Source registry (defined before sidebar so multiselect can reference it) ─
SOURCES: dict[str, str] = {
    "El Universo (Ecuador)":        "https://www.eluniverso.com/rss/",
    "Primicias (Ecuador)":          "https://www.primicias.ec/rss/",
    "El Comercio (Ecuador)":        "https://www.elcomercio.com/rss/",
    "BBC Mundo":                    "https://www.bbc.com/mundo/topics/c8n7z3k8y5zt/rss",
    "Reuters Latin America":        "https://www.reuters.com/world/americas/rss/",
    "InSight Crime":                "https://insightcrime.org/feed/",
    "France 24 Américas":           "https://www.france24.com/es/rss/americas",
    "Crisis Group Latin America":   "https://www.crisisgroup.org/rss/73",
}

SOURCE_ICONS: dict[str, str] = {
    "El Universo":   "🟡",
    "Primicias":     "🔵",
    "El Comercio":   "🟢",
    "BBC":           "🔴",
    "Reuters":       "🟠",
    "InSight Crime": "⚫",
    "France 24":     "🟣",
    "Crisis Group":  "🔷",
}

HIGH_RISK_WORDS = {
    "violencia", "homicidio", "narco", "narcotráfico",
    "asesinato", "crimen", "cocaína", "sicario", "masacre",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Filters & Settings")

dark_mode = st.sidebar.checkbox("🌙 Dark Mode", value=False)

api_key = st.sidebar.text_input(
    "NewsAPI.org Key (free at newsapi.org)", type="password"
)

keywords_input = st.sidebar.text_input(
    "Keywords (comma-separated)",
    "Ecuador, Guayaquil, Posorja, Esmeraldas, narcotráfico, violencia, "
    "cocaína, Fito, Choneros, Lobos, homicidio, puerto",
)

days_back = st.sidebar.slider("Days back", 1, 30, 7)

selected_sources = st.sidebar.multiselect(
    "Sources to include",
    options=["All"] + list(SOURCES.keys()),
    default=["All"],
)

active_sources: list[str] = (
    list(SOURCES.keys())
    if "All" in selected_sources or not selected_sources
    else [s for s in selected_sources if s in SOURCES]
)

keyword_list: list[str] = [
    k.strip().lower() for k in keywords_input.split(",") if k.strip()
]

# ── Dark-mode CSS ─────────────────────────────────────────────────────────────
if dark_mode:
    st.markdown(
        """
        <style>
        .stApp { background-color: #0e1117; color: #fafafa; }
        .stExpander { background-color: #1a1f2e; border-color: #2e2e2e; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def fetch_rss(url: str, days_back: int) -> list[dict]:
    """Fetch up to 30 entries from an RSS feed, filtered by age."""
    cutoff = datetime.now() - timedelta(days=days_back)
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    entries: list[dict] = []
    for entry in feed.entries[:30]:
        pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        pub_date = datetime(*pub_parsed[:6]) if pub_parsed else None
        if pub_date and pub_date < cutoff:
            continue
        entries.append(
            {
                "Title":     entry.get("title", "(no title)"),
                "Source":    feed.feed.get("title", url),
                "Link":      entry.get("link", ""),
                "Published": pub_date.strftime("%Y-%m-%d %H:%M") if pub_date else "Unknown",
                "Summary":   entry.get("summary", "")[:400],
                "_pub_dt":   pub_date or datetime.min,
            }
        )
    return entries


def keyword_match(row: dict, kws: list[str]) -> bool:
    haystack = (row["Title"] + " " + row["Summary"]).lower()
    return any(kw in haystack for kw in kws)


def highlight_keywords(text: str, kws: list[str]) -> str:
    for kw in kws:
        text = re.sub(
            f"({re.escape(kw)})", r"**\1**", text, flags=re.IGNORECASE
        )
    return text


def risk_tag(title: str) -> str:
    tl = title.lower()
    if any(w in tl for w in HIGH_RISK_WORDS):
        return "🔴 High"
    if any(w in tl for w in {"gobierno", "política", "protesta", "huelga"}):
        return "🟡 Medium"
    return "🟢 Low"


def source_icon(source_name: str) -> str:
    for key, icon in SOURCE_ICONS.items():
        if key.lower() in source_name.lower():
            return icon
    return "⚪"


# ── Collect RSS data ──────────────────────────────────────────────────────────
all_news: list[dict] = []
rss_errors: list[str] = []

with st.spinner("Fetching latest public reports…"):
    for name in active_sources:
        try:
            all_news.extend(fetch_rss(SOURCES[name], days_back))
        except Exception as exc:
            rss_errors.append(f"{name}: {exc}")

if rss_errors:
    with st.sidebar.expander("⚠️ RSS errors"):
        for err in rss_errors:
            st.write(err)

# ── NewsAPI ───────────────────────────────────────────────────────────────────
if api_key and keyword_list:
    query = " OR ".join(k.strip() for k in keywords_input.split(",") if k.strip())
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    api_url = (
        "https://newsapi.org/v2/everything"
        f"?q={requests.utils.quote(query)}"
        f"&language=es"
        f"&from={from_date}"
        f"&sortBy=publishedAt"
        f"&pageSize=30"
        f"&apiKey={api_key}"
    )
    try:
        resp = requests.get(api_url, timeout=10).json()
        if resp.get("status") == "ok":
            st.sidebar.success(
                f"NewsAPI ✓ — {resp.get('totalResults', '?')} total results"
            )
            for article in resp.get("articles", []):
                pub_str = article.get("publishedAt", "")
                try:
                    pub_dt = datetime.fromisoformat(
                        pub_str.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except Exception:
                    pub_dt = datetime.min
                all_news.append(
                    {
                        "Title":     article.get("title") or "(no title)",
                        "Source":    article["source"]["name"],
                        "Link":      article.get("url", ""),
                        "Published": (
                            pub_dt.strftime("%Y-%m-%d %H:%M")
                            if pub_dt != datetime.min
                            else pub_str[:10]
                        ),
                        "Summary":   article.get("description") or "",
                        "_pub_dt":   pub_dt,
                    }
                )
        else:
            st.sidebar.error(f"NewsAPI error: {resp.get('message', 'unknown')}")
    except Exception as exc:
        st.sidebar.error(f"NewsAPI request failed: {exc}")

# ── Build & filter DataFrame ──────────────────────────────────────────────────
df = pd.DataFrame(all_news)

if not df.empty:
    if keyword_list:
        df = df[df.apply(lambda row: keyword_match(row, keyword_list), axis=1)]
    df = (
        df.drop_duplicates(subset=["Title"])
        .sort_values("_pub_dt", ascending=False)
        .reset_index(drop=True)
    )
    df["Risk"] = df["Title"].apply(risk_tag)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["📋 Overview", "📈 Trends", "📊 Raw Data", "⬇️ Export"]
)

# ── Tab 1 : Overview ──────────────────────────────────────────────────────────
with tab1:
    if df.empty:
        st.info(
            "No articles matched your keywords. "
            "Try broader terms or add your NewsAPI key."
        )
    else:
        st.subheader(f"📰 Recent Matches — {len(df)} articles")

        # Quick risk summary
        col_h, col_m, col_l = st.columns(3)
        col_h.metric("🔴 High Risk",   len(df[df["Risk"] == "🔴 High"]))
        col_m.metric("🟡 Medium Risk", len(df[df["Risk"] == "🟡 Medium"]))
        col_l.metric("🟢 Low Risk",    len(df[df["Risk"] == "🟢 Low"]))

        st.divider()

        for _, row in df.iterrows():
            icon = source_icon(row["Source"])
            highlighted = highlight_keywords(row["Summary"], keyword_list)
            label = (
                f"{icon} {row['Risk']}  |  **{row['Title']}**  "
                f"— {row['Source']} • {row['Published']}"
            )
            with st.expander(label):
                if highlighted:
                    st.markdown(highlighted)
                else:
                    st.write("_(no summary available)_")
                st.markdown(f"[Read full article →]({row['Link']})")

# ── Tab 2 : Trends ────────────────────────────────────────────────────────────
with tab2:
    if df.empty:
        st.info("No data to chart yet.")
    else:
        chart_df = df[df["Published"] != "Unknown"].copy()
        chart_df["Date"] = chart_df["Published"].str[:10]

        st.subheader("Articles per day")
        counts = chart_df.groupby("Date").size().reset_index(name="Articles")
        st.bar_chart(counts.set_index("Date"), use_container_width=True)

        st.subheader("Articles by source")
        by_source = chart_df.groupby("Source").size().reset_index(name="Count")
        st.bar_chart(by_source.set_index("Source"), use_container_width=True)

        st.subheader("Risk distribution")
        risk_counts = df["Risk"].value_counts().reset_index()
        risk_counts.columns = ["Risk", "Count"]
        st.bar_chart(risk_counts.set_index("Risk"), use_container_width=True)

# ── Tab 3 : Raw data table ────────────────────────────────────────────────────
with tab3:
    if df.empty:
        st.info("No data yet.")
    else:
        display_cols = ["Risk", "Title", "Source", "Published", "Link"]
        st.dataframe(
            df[display_cols],
            use_container_width=True,
            column_config={
                "Link": st.column_config.LinkColumn("Link"),
            },
        )

# ── Tab 4 : Export ────────────────────────────────────────────────────────────
with tab4:
    if df.empty:
        st.info("No data to export yet.")
    else:
        export_cols = ["Risk", "Title", "Source", "Published", "Link", "Summary"]
        csv_bytes = df[export_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_bytes,
            file_name=f"ecuador_osint_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
        )
        st.caption(f"{len(df)} articles ready to export.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "✅ All sources public & openly available  •  "
    "Respect each site's terms of service  •  "
    "Educational / research use only"
)
