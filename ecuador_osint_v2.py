"""
Ecuador OSINT Dashboard v3.0 — NGO / Human Rights Edition
==========================================================
Full analyst toolkit:
  • 8 curated public RSS feeds (security, politics, humanitarian)
  • NewsAPI integration
  • ACLED conflict data (free API)
  • Named Entity extraction (spaCy es_core_news_sm)
  • Sentiment analysis (TextBlob + Spanish lexicon)
  • Interactive Folium map of incident locations
  • Timeline chart
  • Entity frequency chart
  • Incident tagging & severity scoring
  • CSV + JSON export
  • Briefing note auto-generator

Install:
  pip install streamlit pandas feedparser requests folium \
              streamlit-folium textblob spacy plotly
  python -m spacy download es_core_news_sm
  python -m textblob.download_corpora

Run:
  streamlit run ecuador_osint_v2.py
"""

# ── stdlib ────────────────────────────────────────────────────────────────────
import json
import re
import textwrap
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# ── third-party ───────────────────────────────────────────────────────────────
import feedparser
import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_folium import st_folium
from textblob import TextBlob

# ── Secrets (Streamlit Cloud) or fall back to sidebar inputs ──────────────────
_secrets_newsapi = st.secrets.get("NEWSAPI_KEY", "") if hasattr(st, "secrets") else ""
_secrets_acled_key = st.secrets.get("ACLED_KEY", "") if hasattr(st, "secrets") else ""
_secrets_acled_email = st.secrets.get("ACLED_EMAIL", "") if hasattr(st, "secrets") else ""

# spaCy is optional — gracefully degrade if not installed
try:
    import spacy
    SPACY_OK = True
except ImportError:
    SPACY_OK = False


@st.cache_resource
def _load_spacy():
    """Load spaCy model once and cache across reruns."""
    try:
        return spacy.load("es_core_news_sm")
    except Exception:
        return None


nlp = _load_spacy() if SPACY_OK else None
if nlp is None:
    SPACY_OK = False

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ecuador OSINT · Human Rights Edition",
    page_icon="🇪🇨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS  — dark editorial aesthetic, sharp & professional
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:ital,wght@0,300;0,600;1,300&display=swap');

:root {
    --bg:        #0a0c10;
    --surface:   #111418;
    --border:    #1e2530;
    --accent:    #e8c547;
    --danger:    #e05252;
    --warn:      #e09a3a;
    --ok:        #52b788;
    --text:      #d4dbe8;
    --muted:     #6b7a94;
    --mono:      'IBM Plex Mono', monospace;
    --sans:      'IBM Plex Sans', sans-serif;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans);
}
[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border);
}
h1,h2,h3,h4 { font-family: var(--mono); color: var(--accent); letter-spacing: -0.5px; }
.stTabs [data-baseweb="tab-list"] { background: var(--surface); border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] { color: var(--muted); font-family: var(--mono); font-size: 0.8rem; }
.stTabs [aria-selected="true"] { color: var(--accent) !important; border-bottom: 2px solid var(--accent); }
.stExpander { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 4px; }
.stMetric { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 12px; }
[data-testid="stMetricValue"] { font-family: var(--mono); color: var(--accent); }
.stDownloadButton button { background: var(--accent); color: #000; font-family: var(--mono); font-weight: 600; border: none; }
.stButton button { background: transparent; color: var(--accent); border: 1px solid var(--accent); font-family: var(--mono); }
.severity-high   { color: var(--danger); font-family: var(--mono); font-weight: 600; }
.severity-medium { color: var(--warn);   font-family: var(--mono); font-weight: 600; }
.severity-low    { color: var(--ok);     font-family: var(--mono); font-weight: 600; }
.tag { display: inline-block; padding: 1px 8px; border-radius: 2px; font-family: var(--mono);
       font-size: 0.72rem; margin: 1px; background: var(--border); color: var(--text); }
hr { border-color: var(--border); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='border-bottom:1px solid #1e2530; padding-bottom:1rem; margin-bottom:1.5rem;'>
  <span style='font-family:"IBM Plex Mono",monospace; font-size:0.7rem; color:#6b7a94; letter-spacing:2px;'>
    NGO · HUMAN RIGHTS · OPEN SOURCE INTELLIGENCE
  </span><br>
  <span style='font-family:"IBM Plex Mono",monospace; font-size:1.8rem; color:#e8c547; font-weight:600;'>
    🇪🇨 ECUADOR OSINT DASHBOARD
  </span>
  <span style='font-family:"IBM Plex Mono",monospace; font-size:0.7rem; color:#6b7a94; float:right; padding-top:1rem;'>
    v3.0 · PUBLIC SOURCES ONLY · EDUCATIONAL USE
  </span>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
SOURCES: dict[str, str] = {
    "El Universo":          "https://www.eluniverso.com/rss/",
    "Primicias":            "https://www.primicias.ec/rss/",
    "El Comercio":          "https://www.elcomercio.com/rss/",
    "BBC Mundo":            "https://www.bbc.com/mundo/topics/c8n7z3k8y5zt/rss",
    "Reuters LatAm":        "https://www.reuters.com/world/americas/rss/",
    "InSight Crime":        "https://insightcrime.org/feed/",
    "France 24 Américas":   "https://www.france24.com/es/rss/americas",
    "Crisis Group LatAm":   "https://www.crisisgroup.org/rss/73",
    "OHCHR News":           "https://www.ohchr.org/en/rss/NewsEvents",
    "Human Rights Watch":   "https://www.hrw.org/rss/news",
    "Global Voices LatAm":  "https://globalvoices.org/world/latin-america/rss/",
}

# Keyword taxonomy by theme
KEYWORD_THEMES: dict[str, list[str]] = {
    "Security & Crime": [
        "narcotráfico", "cocaína", "homicidio", "violencia", "asesinato",
        "sicario", "masacre", "crimen", "Los Choneros", "Lobos", "Fito",
        "extorsión", "banda", "secuestro", "prison", "cárcel", "pandilla",
    ],
    "Political": [
        "Noboa", "Correa", "gobierno", "presidente", "asamblea",
        "elecciones", "política", "ministro", "estado de excepción",
        "decreto", "congreso", "correísmo",
    ],
    "Humanitarian": [
        "desplazado", "refugiado", "derechos humanos", "pobreza",
        "migración", "ACNUR", "CICR", "Cruz Roja", "comunidad",
        "indígena", "víctima", "protección", "humanitario",
    ],
    "Economic": [
        "economía", "petróleo", "exportación", "puerto", "Guayaquil",
        "Posorja", "dolarización", "FMI", "deuda", "inversión",
    ],
}

# Severity scoring words
HIGH_SEVERITY = {
    "masacre", "asesinato", "homicidio", "sicario", "bomba", "ataque",
    "muerte", "muerto", "víctima", "secuestro", "desaparecido",
    "tortura", "ejecución", "violación", "matanza",
}
MEDIUM_SEVERITY = {
    "violencia", "crimen", "narcotráfico", "extorsión", "amenaza",
    "detenido", "arrestado", "operación", "banda", "pandilla",
    "protesta", "disturbio", "represión", "desplazado",
}

# Key Ecuador locations for geocoding (lat, lon)
LOCATION_COORDS: dict[str, tuple[float, float]] = {
    "guayaquil":    (-2.1894, -79.8891),
    "quito":        (-0.1807, -78.4678),
    "esmeraldas":   (0.9592, -79.6516),
    "manta":        (-0.9677, -80.7089),
    "cuenca":       (-2.9001, -79.0059),
    "portoviejo":   (-1.0546, -80.4545),
    "machala":      (-3.2581, -79.9554),
    "santo domingo": (-0.2526, -79.1719),
    "loja":         (-3.9931, -79.2042),
    "ambato":       (-1.2543, -78.6228),
    "posorja":      (-2.6833, -80.2333),
    "tumaco":       (1.8002, -78.7772),
    "cali":         (3.4516, -76.5320),
    "bogotá":       (4.7110, -74.0721),
    "colombia":     (4.5709, -74.2973),
    "perú":         (-9.1900, -75.0152),
}

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.divider()

    newsapi_key = st.text_input("NewsAPI.org Key", value=_secrets_newsapi,
                                type="password",
                                help="Free key at newsapi.org — 100 req/day")
    acled_key   = st.text_input("ACLED API Key", value=_secrets_acled_key,
                                type="password",
                                help="Free at acleddata.com — conflict incident data")
    acled_email = st.text_input("ACLED Email", value=_secrets_acled_email,
                                help="Required alongside ACLED key")

    st.divider()
    st.markdown("### 📅 Time range")
    days_back = st.slider("Days back", 1, 90, 14)

    st.divider()
    st.markdown("### 🗞️ Sources")
    selected_sources = st.multiselect(
        "Active feeds",
        options=list(SOURCES.keys()),
        default=list(SOURCES.keys()),
    )

    st.divider()
    st.markdown("### 🔍 Keyword themes")
    active_themes = st.multiselect(
        "Include themes",
        options=list(KEYWORD_THEMES.keys()),
        default=list(KEYWORD_THEMES.keys()),
    )
    extra_keywords = st.text_input(
        "Extra keywords (comma separated)", ""
    )

    st.divider()
    st.markdown("### 🎚️ Filters")
    severity_filter = st.multiselect(
        "Severity",
        ["🔴 High", "🟡 Medium", "🟢 Low"],
        default=["🔴 High", "🟡 Medium", "🟢 Low"],
    )
    min_articles = st.number_input("Min articles to show map", 1, 50, 3)

# Build combined keyword list
keyword_list: list[str] = []
for theme in active_themes:
    keyword_list.extend(KEYWORD_THEMES.get(theme, []))
if extra_keywords:
    keyword_list.extend([k.strip().lower() for k in extra_keywords.split(",") if k.strip()])
keyword_list = list(set(k.lower() for k in keyword_list))

# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

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


def extract_entities(text: str) -> dict[str, list[str]]:
    if not SPACY_OK:
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


def generate_briefing(df: pd.DataFrame, acled_df: pd.DataFrame) -> str:
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


# ─────────────────────────────────────────────────────────────────────────────
# DATA COLLECTION
# ─────────────────────────────────────────────────────────────────────────────
all_news: list[dict] = []
rss_errors: list[str] = []

with st.spinner("📡 Fetching public feeds…"):
    def _fetch_one(name: str) -> tuple[str, list[dict] | None, str | None]:
        url = SOURCES.get(name)
        if not url:
            return name, [], None
        try:
            return name, fetch_rss(url, days_back), None
        except Exception as e:
            return name, None, f"{name}: {e}"

    with ThreadPoolExecutor(max_workers=max(len(selected_sources), 1)) as pool:
        futures = {pool.submit(_fetch_one, name): name for name in selected_sources}
        for fut in as_completed(futures, timeout=30):
            try:
                name, results, err = fut.result(timeout=15)
            except Exception:
                rss_errors.append(f"{futures[fut]}: timed out")
                continue
            if err:
                rss_errors.append(err)
            elif results:
                all_news.extend(results)

if newsapi_key and keyword_list:
    with st.spinner("📰 Fetching NewsAPI…"):
        newsapi_results = fetch_newsapi(newsapi_key, keyword_list, days_back)
        all_news.extend(newsapi_results)

# ACLED
acled_df = pd.DataFrame()
if acled_key and acled_email:
    with st.spinner("🗺️ Fetching ACLED conflict data…"):
        acled_df = fetch_acled(acled_email, acled_key, days_back)

# ─────────────────────────────────────────────────────────────────────────────
# BUILD DATAFRAME
# ─────────────────────────────────────────────────────────────────────────────
df = pd.DataFrame(all_news)

if not df.empty:
    # Keyword filter
    if keyword_list:
        df = df[df.apply(lambda r: keyword_match(r, keyword_list), axis=1)]

    df = df.drop_duplicates(subset=["Title"]).reset_index(drop=True)

    # Enrichment
    with st.spinner("🧠 Analysing articles…"):
        df["Severity"]  = df.apply(lambda r: compute_severity(r["Title"], r["Summary"]), axis=1)
        df["Sentiment"], df["Sentiment_Score"] = zip(*df.apply(
            lambda r: compute_sentiment(r["Title"] + " " + r["Summary"]), axis=1))
        df["Themes"]    = df.apply(lambda r: tag_themes(r["Title"], r["Summary"]), axis=1)
        df["Locations"] = df.apply(lambda r: detect_locations(r["Title"] + " " + r["Summary"]), axis=1)

    # Severity filter
    df = df[df["Severity"].isin(severity_filter)]
    df = df.sort_values("_pub_dt", ascending=False).reset_index(drop=True)

# ─────────────────────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────────────────────
if not df.empty:
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Articles",    len(df))
    k2.metric("🔴 High Severity",  len(df[df["Severity"] == "🔴 High"]))
    k3.metric("🟡 Medium",         len(df[df["Severity"] == "🟡 Medium"]))
    k4.metric("Sources Active",    df["Source"].nunique())
    k5.metric("ACLED Events",      len(acled_df) if not acled_df.empty else "—")
    k6.metric("Period (days)",     days_back)
    st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📋 Feed",
    "🗺️ Incident Map",
    "📈 Analytics",
    "🧩 Entities",
    "⚔️ ACLED Data",
    "📄 Briefing",
    "📊 Raw Data",
    "⬇️ Export",
])
tab_feed, tab_map, tab_analytics, tab_entities, tab_acled, tab_brief, tab_raw, tab_export = tabs

# ── TAB 1: FEED ───────────────────────────────────────────────────────────────
with tab_feed:
    if df.empty:
        st.info("No articles matched current filters. Try expanding keywords or time range.")
    else:
        st.markdown(f"### 📰 {len(df)} articles matched")

        # Search box
        search = st.text_input("🔎 Search within results", "")
        view_df = df.copy()
        if search:
            view_df = view_df[
                view_df["Title"].str.contains(search, case=False, na=False) |
                view_df["Summary"].str.contains(search, case=False, na=False)
            ]

        for _, row in view_df.iterrows():
            sev = row["Severity"]
            sev_class = {"🔴 High": "severity-high", "🟡 Medium": "severity-medium"}.get(sev, "severity-low")
            themes_html = " ".join(f'<span class="tag">{t}</span>' for t in row.get("Themes", []))
            sent = row.get("Sentiment", "")
            sent_icon = {"Negative": "😟", "Positive": "🙂", "Neutral": "😐"}.get(sent, "")

            with st.expander(f"{sev}  {row['Title']}  —  {row['Source']} · {row['Published'][:10]}"):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    highlighted = highlight(row["Summary"], keyword_list)
                    st.markdown(highlighted)
                    st.markdown(themes_html, unsafe_allow_html=True)
                    st.markdown(f"[→ Read full article]({row['Link']})")
                with col_b:
                    st.markdown(f"**Sentiment:** {sent_icon} {sent}")
                    st.markdown(f"**Score:** `{row.get('Sentiment_Score', 0):.3f}`")
                    locs = row.get("Locations", [])
                    if locs:
                        st.markdown("**Locations:**")
                        for loc, *_ in locs:
                            st.markdown(f"  📍 {loc}")

# ── TAB 2: MAP ────────────────────────────────────────────────────────────────
with tab_map:
    st.markdown("### 🗺️ Incident Location Map")
    st.caption("Locations inferred from article text. ACLED points shown if API key provided.")

    m = folium.Map(
        location=[-1.8, -78.2],
        zoom_start=6,
        tiles="CartoDB dark_matter",
    )

    # Plot news-derived locations
    plotted = 0
    for _, row in df.iterrows():
        locs = row.get("Locations", [])
        for loc_name, lat, lon in locs:
            color = {"🔴 High": "red", "🟡 Medium": "orange"}.get(row["Severity"], "green")
            folium.CircleMarker(
                location=[lat, lon],
                radius=7,
                color=color,
                fill=True,
                fill_opacity=0.8,
                popup=folium.Popup(
                    f"<b>{row['Title'][:80]}</b><br>"
                    f"{row['Source']} · {row['Published'][:10]}<br>"
                    f"Severity: {row['Severity']}<br>"
                    f"<a href='{row['Link']}' target='_blank'>Read →</a>",
                    max_width=300,
                ),
                tooltip=f"{loc_name} — {row['Severity']}",
            ).add_to(m)
            plotted += 1

    # Plot ACLED events
    if not acled_df.empty:
        for _, ev in acled_df.iterrows():
            try:
                lat = float(ev.get("latitude", 0))
                lon = float(ev.get("longitude", 0))
                folium.Marker(
                    location=[lat, lon],
                    icon=folium.Icon(color="purple", icon="exclamation-sign", prefix="glyphicon"),
                    popup=folium.Popup(
                        f"<b>ACLED: {ev.get('event_type','')}</b><br>"
                        f"{ev.get('sub_event_type','')}<br>"
                        f"Actor: {ev.get('actor1','')}<br>"
                        f"Location: {ev.get('location','')}<br>"
                        f"Date: {ev.get('event_date','')}<br>"
                        f"Fatalities: {ev.get('fatalities',0)}<br>"
                        f"<small>{str(ev.get('notes',''))[:200]}</small>",
                        max_width=320,
                    ),
                    tooltip=f"ACLED: {ev.get('event_type','')} — {ev.get('location','')}",
                ).add_to(m)
            except Exception:
                continue

    # Legend
    legend_html = """
    <div style='position:fixed;bottom:30px;left:30px;background:#111;padding:10px;
                border:1px solid #333;border-radius:4px;font-family:monospace;font-size:11px;color:#d4dbe8;'>
    <b>Legend</b><br>
    🔴 High severity (news)<br>
    🟡 Medium severity (news)<br>
    🟢 Low severity (news)<br>
    🟣 ACLED conflict event<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(m, width=None, height=550, returned_objects=[])

    if plotted == 0 and acled_df.empty:
        st.warning("No locatable incidents found. Add ACLED credentials for richer map data.")

# ── TAB 3: ANALYTICS ─────────────────────────────────────────────────────────
with tab_analytics:
    if df.empty:
        st.info("No data to analyse.")
    else:
        st.markdown("### 📈 Trend Analytics")

        col_l, col_r = st.columns(2)

        # Timeline
        with col_l:
            chart_df = df[df["Published"] != "Unknown"].copy()
            chart_df["Date"] = pd.to_datetime(chart_df["Published"].str[:10])
            daily = chart_df.groupby(["Date", "Severity"]).size().reset_index(name="Count")
            fig = px.bar(
                daily, x="Date", y="Count", color="Severity",
                color_discrete_map={"🔴 High": "#e05252", "🟡 Medium": "#e09a3a", "🟢 Low": "#52b788"},
                title="Articles per day by severity",
                template="plotly_dark",
            )
            fig.update_layout(paper_bgcolor="#0a0c10", plot_bgcolor="#111418",
                              font_family="IBM Plex Mono")
            st.plotly_chart(fig, use_container_width=True)

        # Source distribution
        with col_r:
            src_counts = df["Source"].value_counts().reset_index()
            src_counts.columns = ["Source", "Count"]
            fig2 = px.bar(
                src_counts, x="Count", y="Source", orientation="h",
                title="Articles by source", template="plotly_dark",
                color="Count", color_continuous_scale="YlOrRd",
            )
            fig2.update_layout(paper_bgcolor="#0a0c10", plot_bgcolor="#111418",
                               font_family="IBM Plex Mono", showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        col_l2, col_r2 = st.columns(2)

        # Theme distribution
        with col_l2:
            theme_list = df["Themes"].explode().dropna()
            theme_counts = theme_list.value_counts().reset_index()
            theme_counts.columns = ["Theme", "Count"]
            fig3 = px.pie(theme_counts, names="Theme", values="Count",
                          title="Theme distribution", template="plotly_dark",
                          color_discrete_sequence=px.colors.sequential.YlOrRd)
            fig3.update_layout(paper_bgcolor="#0a0c10", font_family="IBM Plex Mono")
            st.plotly_chart(fig3, use_container_width=True)

        # Sentiment over time
        with col_r2:
            sent_df = chart_df.copy()
            sent_df["Sentiment_Score"] = df.loc[chart_df.index, "Sentiment_Score"]
            daily_sent = sent_df.groupby("Date")["Sentiment_Score"].mean().reset_index()
            fig4 = px.line(
                daily_sent, x="Date", y="Sentiment_Score",
                title="Average daily sentiment score",
                template="plotly_dark",
            )
            fig4.add_hline(y=0, line_dash="dash", line_color="#6b7a94")
            fig4.update_traces(line_color="#e8c547")
            fig4.update_layout(paper_bgcolor="#0a0c10", plot_bgcolor="#111418",
                               font_family="IBM Plex Mono")
            st.plotly_chart(fig4, use_container_width=True)

# ── TAB 4: ENTITIES ───────────────────────────────────────────────────────────
with tab_entities:
    st.markdown("### 🧩 Named Entity Extraction")
    if not SPACY_OK:
        st.warning(
            "spaCy model not loaded. Install with:\n\n"
            "```\npip install spacy\npython -m spacy download es_core_news_sm\n```"
        )
    elif df.empty:
        st.info("No articles to analyse.")
    else:
        all_entities: dict[str, list[str]] = {}
        sample = df.head(50)  # limit for performance
        for _, row in sample.iterrows():
            ents = extract_entities(row["Title"] + " " + row["Summary"])
            for label, vals in ents.items():
                all_entities.setdefault(label, []).extend(vals)

        if not all_entities:
            st.info("No entities extracted. Try more articles or check spaCy model.")
        else:
            label_map = {
                "PER": "👤 People", "ORG": "🏢 Organizations",
                "GPE": "📍 Places", "LOC": "🗺️ Locations",
                "MISC": "🔖 Other",
            }
            cols = st.columns(min(len(all_entities), 3))
            for i, (label, vals) in enumerate(all_entities.items()):
                counts = Counter(vals).most_common(15)
                readable = label_map.get(label, label)
                with cols[i % len(cols)]:
                    st.markdown(f"**{readable}**")
                    ent_df = pd.DataFrame(counts, columns=["Entity", "Count"])
                    fig = px.bar(ent_df, x="Count", y="Entity", orientation="h",
                                 template="plotly_dark",
                                 color="Count", color_continuous_scale="YlOrRd")
                    fig.update_layout(
                        paper_bgcolor="#0a0c10", plot_bgcolor="#111418",
                        font_family="IBM Plex Mono", height=350,
                        showlegend=False, margin=dict(l=0, r=0, t=20, b=0),
                    )
                    st.plotly_chart(fig, use_container_width=True)

# ── TAB 5: ACLED ─────────────────────────────────────────────────────────────
with tab_acled:
    st.markdown("### ⚔️ ACLED Conflict Event Data")
    st.caption("Armed Conflict Location & Event Data Project — acleddata.com (free registration required)")

    if acled_df.empty:
        st.info(
            "No ACLED data loaded. Enter your ACLED API key and email in the sidebar.\n\n"
            "Register free at [acleddata.com](https://acleddata.com/register/). "
            "Provides verified, geocoded conflict event data for Ecuador."
        )
    else:
        a1, a2, a3, a4 = st.columns(4)
        fat_col = "fatalities"
        total_fat = pd.to_numeric(acled_df.get(fat_col, pd.Series([0])), errors="coerce").sum()
        a1.metric("Total Events", len(acled_df))
        a2.metric("Total Fatalities", int(total_fat))
        if "event_type" in acled_df.columns:
            a3.metric("Event Types", acled_df["event_type"].nunique())
        if "location" in acled_df.columns:
            a4.metric("Locations", acled_df["location"].nunique())

        if "event_type" in acled_df.columns:
            fig = px.histogram(acled_df, x="event_type", title="Events by type",
                               template="plotly_dark", color="event_type",
                               color_discrete_sequence=px.colors.sequential.YlOrRd)
            fig.update_layout(paper_bgcolor="#0a0c10", plot_bgcolor="#111418",
                              font_family="IBM Plex Mono", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        display_cols = [c for c in ["event_date", "event_type", "sub_event_type",
                                     "actor1", "location", "fatalities", "notes"]
                        if c in acled_df.columns]
        st.dataframe(acled_df[display_cols], use_container_width=True, height=400)

# ── TAB 6: BRIEFING ───────────────────────────────────────────────────────────
with tab_brief:
    st.markdown("### 📄 Auto-Generated Situation Report")
    st.caption("Structured briefing note from current data — review & edit before use.")

    if df.empty:
        st.info("Load articles first to generate a briefing.")
    else:
        if st.button("⚡ Generate Briefing Note"):
            with st.spinner("Compiling briefing…"):
                brief_text = generate_briefing(df, acled_df)
            st.markdown(brief_text)
            st.download_button(
                "⬇️ Download Briefing (.md)",
                brief_text.encode("utf-8"),
                f"ecuador_sitrep_{datetime.now():%Y%m%d_%H%M}.md",
                "text/markdown",
            )

# ── TAB 7: RAW DATA ───────────────────────────────────────────────────────────
with tab_raw:
    st.markdown("### 📊 Raw Article Data")
    if df.empty:
        st.info("No data yet.")
    else:
        show_cols = ["Severity", "Sentiment", "Title", "Source", "Published", "Themes", "Link"]
        show_cols = [c for c in show_cols if c in df.columns]
        st.dataframe(
            df[show_cols], use_container_width=True,
            height=600,
            column_config={"Link": st.column_config.LinkColumn()},
        )

# ── TAB 8: EXPORT ─────────────────────────────────────────────────────────────
with tab_export:
    st.markdown("### ⬇️ Export Data")

    if df.empty:
        st.info("No data to export.")
    else:
        exp_df = df.copy()
        exp_df["Themes"] = exp_df["Themes"].apply(lambda x: "; ".join(x) if isinstance(x, list) else x)
        exp_df["Locations"] = exp_df["Locations"].apply(
            lambda x: "; ".join(loc[0] for loc in x) if isinstance(x, list) else x
        )

        export_cols = ["Severity", "Sentiment", "Sentiment_Score", "Themes",
                       "Locations", "Title", "Source", "Published", "Link", "Summary"]
        export_cols = [c for c in export_cols if c in exp_df.columns]

        col1, col2 = st.columns(2)

        with col1:
            csv_bytes = exp_df[export_cols].to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download CSV",
                csv_bytes,
                f"ecuador_osint_{datetime.now():%Y%m%d_%H%M}.csv",
                "text/csv",
                use_container_width=True,
            )

        with col2:
            json_bytes = exp_df[export_cols].to_json(
                orient="records", force_ascii=False, indent=2
            ).encode("utf-8")
            st.download_button(
                "📥 Download JSON",
                json_bytes,
                f"ecuador_osint_{datetime.now():%Y%m%d_%H%M}.json",
                "application/json",
                use_container_width=True,
            )

        if not acled_df.empty:
            acled_csv = acled_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download ACLED Data (CSV)",
                acled_csv,
                f"ecuador_acled_{datetime.now():%Y%m%d}.csv",
                "text/csv",
                use_container_width=True,
            )

        st.caption(f"{len(df)} articles ready · All public sources · Educational use only")

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR ERRORS & STATUS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.divider()
    if rss_errors:
        with st.expander(f"⚠️ {len(rss_errors)} feed error(s)"):
            for e in rss_errors:
                st.caption(e)
    if not SPACY_OK:
        st.warning("spaCy not loaded — entity extraction disabled")
    st.caption("v3.0 · Public sources only · No social media scraping · NGO/research use")
