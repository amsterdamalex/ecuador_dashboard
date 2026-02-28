"""
Ecuador OSINT Dashboard v3.0 — NGO / Human Rights Edition
==========================================================
Streamlit entrypoint. All business logic lives in config.py, analysis.py,
and fetchers.py.

Run:
  streamlit run app.py
"""

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG — must be the VERY FIRST Streamlit command, before anything else
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ecuador OSINT · Human Rights Edition",
    page_icon="🇪🇨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Now safe to import everything else ────────────────────────────────────────
from collections import Counter
from datetime import datetime

import pandas as pd

_import_errors: list[str] = []

try:
    import folium
    from streamlit_folium import st_folium
except ImportError as e:
    _import_errors.append(f"Map disabled: {e}")
    folium = None  # type: ignore[assignment]

try:
    import plotly.express as px
except ImportError as e:
    _import_errors.append(f"Charts disabled: {e}")
    px = None  # type: ignore[assignment]

try:
    from analysis import (
        compute_severity,
        compute_sentiment,
        detect_locations,
        extract_entities,
        generate_briefing,
        highlight,
        keyword_match,
        tag_themes,
    )
except ImportError as e:
    _import_errors.append(f"Analysis module failed: {e}")

try:
    from config import KEYWORD_THEMES, SOURCES
except ImportError as e:
    _import_errors.append(f"Config module failed: {e}")
    KEYWORD_THEMES = {}
    SOURCES = {}

try:
    from fetchers import fetch_acled, fetch_all_rss, fetch_newsapi
except ImportError as e:
    _import_errors.append(f"Fetchers module failed: {e}")


# ── spaCy (lazy — loaded only when Entities tab is used) ─────────────────────
@st.cache_resource
def _load_spacy():
    """Load spaCy model once and cache across reruns."""
    try:
        import spacy
        return spacy.load("es_core_news_sm")
    except Exception:
        return None

# ── Secrets (Streamlit Cloud) or fall back to sidebar inputs ──────────────────
try:
    _secrets_newsapi = st.secrets.get("NEWSAPI_KEY", "")
    _secrets_acled_key = st.secrets.get("ACLED_KEY", "")
    _secrets_acled_email = st.secrets.get("ACLED_EMAIL", "")
except Exception:
    _secrets_newsapi = ""
    _secrets_acled_key = ""
    _secrets_acled_email = ""

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
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
    --mono:      'IBM Plex Mono', ui-monospace, SFMono-Regular, monospace;
    --sans:      'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
<link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:ital,wght@0,300;0,600;1,300&display=swap"
      rel="stylesheet" media="print" onload="this.media='all'">
""", unsafe_allow_html=True)

# ── Show import errors (if any) so the user sees what's wrong ─────────────────
if _import_errors:
    for err in _import_errors:
        st.error(err)

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
# DATA COLLECTION (fault-tolerant — app renders even if feeds fail)
# ─────────────────────────────────────────────────────────────────────────────
all_news: list[dict] = []
rss_errors: list[str] = []
acled_df = pd.DataFrame()

try:
    with st.spinner("📡 Fetching public feeds…"):
        source_urls = {name: SOURCES[name] for name in selected_sources if name in SOURCES}
        all_news, rss_errors = fetch_all_rss(source_urls, days_back)
except Exception as exc:
    rss_errors.append(f"RSS fetch failed: {exc}")

if newsapi_key and keyword_list:
    try:
        with st.spinner("📰 Fetching NewsAPI…"):
            newsapi_results = fetch_newsapi(newsapi_key, keyword_list, days_back)
            all_news.extend(newsapi_results)
    except Exception:
        rss_errors.append("NewsAPI fetch failed")

if acled_key and acled_email:
    try:
        with st.spinner("🗺️ Fetching ACLED conflict data…"):
            acled_df = fetch_acled(acled_email, acled_key, days_back)
    except Exception:
        rss_errors.append("ACLED fetch failed")

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
    nlp = _load_spacy()  # lazy — only loaded when this tab renders
    if nlp is None:
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
            ents = extract_entities(row["Title"] + " " + row["Summary"], nlp)
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
                brief_text = generate_briefing(df, acled_df, days_back)
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
    if _load_spacy() is None:
        st.warning("spaCy not loaded — entity extraction disabled")
    st.caption("v3.0 · Public sources only · No social media scraping · NGO/research use")
