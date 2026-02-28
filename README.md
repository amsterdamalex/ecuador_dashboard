<div align="center">

# Ecuador OSINT Dashboard

### Open-Source Intelligence Platform · NGO & Human Rights Edition

[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-Educational_Use-yellow?style=flat-square)](#disclaimer)
[![Sources](https://img.shields.io/badge/Sources-Public_Only-52b788?style=flat-square)](#data-sources)
[![ACLED](https://img.shields.io/badge/ACLED-Integrated-e05252?style=flat-square)](https://acleddata.com)
[![Tests](https://img.shields.io/badge/Tests-56_passing-52b788?style=flat-square)](#testing)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](#docker)

**Real-time monitoring of security, political, and humanitarian developments in Ecuador.**
Built exclusively on open, public data sources. No scraping. No MILINT. Research & NGO use only.

[Live Demo](#) · [Report Bug](https://github.com/amsterdamalex/ecuador_dashboard/issues) · [Request Feature](https://github.com/amsterdamalex/ecuador_dashboard/issues)

---

</div>

## ◈ What This Is

A full open-source intelligence dashboard for Ecuador, purpose-built for **NGO analysts, human rights researchers, and journalists** who need to monitor fast-moving security, political, and humanitarian situations without access to proprietary intelligence tools.

It pulls from 11 curated public feeds, applies NLP enrichment (sentiment scoring, named entity extraction, severity tagging), plots geocoded incidents on an interactive map, and generates structured situation reports — all in a browser, for free.

---

## ◈ Features

### 📡 Data Ingestion

| Source | Type | Coverage |
|--------|------|----------|
| El Universo | RSS | Ecuador national |
| Primicias | RSS | Ecuador investigative |
| El Comercio | RSS | Ecuador national |
| BBC Mundo | RSS | Latin America |
| Reuters LatAm | RSS | Regional |
| InSight Crime | RSS | Organized crime |
| France 24 Américas | RSS | Regional |
| Crisis Group LatAm | RSS | Conflict analysis |
| OHCHR | RSS | Human rights |
| Human Rights Watch | RSS | Human rights |
| Global Voices LatAm | RSS | Civil society |
| **NewsAPI** | API | +30 articles/query |
| **ACLED** | API | Geocoded conflict events |

### 🧠 Intelligence Enrichment

- **Severity scoring** — automated High / Medium / Low tagging based on incident vocabulary
- **Sentiment analysis** — per-article polarity scoring via TextBlob
- **Named entity extraction** — people, organisations, locations via spaCy Spanish model (`es_core_news_sm`)
- **Theme classification** — Security, Political, Humanitarian, Economic
- **Location detection** — matched against 15+ Ecuador & regional coordinates

### 📊 Analyst Interface

```
┌─────────────────────────────────────────────────────────────┐
│  Tab 1 · Feed          Keyword-highlighted articles          │
│  Tab 2 · Incident Map  Folium map, severity colour-coded     │
│  Tab 3 · Analytics     Timeline · Source · Theme · Sentiment │
│  Tab 4 · Entities      NER frequency charts by type          │
│  Tab 5 · ACLED Data    Verified conflict event table         │
│  Tab 6 · Briefing      Auto-generated situation report       │
│  Tab 7 · Raw Data      Sortable full article table           │
│  Tab 8 · Export        CSV + JSON + ACLED CSV download       │
└─────────────────────────────────────────────────────────────┘
```

---

## ◈ Quick Start

### 1 · Clone & install

```bash
git clone https://github.com/amsterdamalex/ecuador_dashboard.git
cd ecuador_dashboard

pip install -r requirements.txt
python -m textblob.download_corpora
```

### 2 · Run

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### 3 · Configure (optional but recommended)

| Key | Where to get it | What it unlocks |
|-----|----------------|-----------------|
| **NewsAPI** | [newsapi.org](https://newsapi.org) — free | +30 Spanish-language articles per query |
| **ACLED API + Email** | [acleddata.com/register](https://acleddata.com/register/) — free for NGOs | Geocoded, verified conflict event data |

Paste keys directly into the sidebar at runtime. No `.env` file needed for local use.

---

## ◈ Docker

Build and run with a single command — no local Python setup needed:

```bash
docker compose up --build
```

Opens at `http://localhost:8501`. All dependencies are pre-installed in the image.

To pass API keys via environment:

```bash
# Create a .env file (git-ignored)
echo 'NEWSAPI_KEY=your_key_here' >> .env
echo 'ACLED_KEY=your_key_here' >> .env
echo 'ACLED_EMAIL=you@example.com' >> .env
```

Then uncomment the `env_file` section in `docker-compose.yml`.

---

## ◈ Deploy to Streamlit Cloud

**1.** Push to GitHub (this repo is already set up)

**2.** Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → connect this repo → set main file to `app.py` (or `ecuador_osint_v2.py` — both work)

**3.** Add secrets so keys are pre-loaded (Settings → Secrets):

```toml
NEWSAPI_KEY   = "your_newsapi_key_here"
ACLED_KEY     = "your_acled_key_here"
ACLED_EMAIL   = "your@email.com"
```

**4.** Click Deploy — live in ~2 minutes.

---

## ◈ Project Structure

```
ecuador_dashboard/
├── app.py                ← Streamlit entrypoint (UI wiring)
├── config.py             ← Constants (sources, keywords, locations)
├── analysis.py           ← Pure functions (severity, sentiment, NER, themes)
├── fetchers.py           ← Data fetching with parallel RSS, timeouts, caching
├── ecuador_osint_v2.py   ← Compatibility shim (redirects to app.py)
├── test_dashboard.py     ← 56-test suite
├── requirements.txt      ← All dependencies including spaCy model
├── Dockerfile            ← Production container
├── docker-compose.yml    ← One-command local deployment
├── .dockerignore
├── .gitignore
└── .streamlit/
    └── config.toml       ← Performance tuning (no file watcher, no telemetry)
```

### Module responsibilities

| Module | Lines | Depends on Streamlit? | Purpose |
|--------|------:|:---------------------:|---------|
| `config.py` | ~70 | No | Constants — sources, keyword themes, severity words, geocoordinates |
| `analysis.py` | ~140 | No | Pure functions — severity scoring, sentiment, NER, theme tagging, briefing generation |
| `fetchers.py` | ~130 | Yes (`@st.cache_data`) | Parallel RSS fetching (ThreadPoolExecutor), NewsAPI, ACLED — with timeouts and caching |
| `app.py` | ~620 | Yes | UI — page config, sidebar, tabs, charts, map, export |

---

## ◈ Testing

```bash
pytest test_dashboard.py -v
```

56 tests covering constants validation, all pure analysis functions, and briefing generation. Tests for `config.py` and `analysis.py` require **zero Streamlit mocks** — they import directly.

---

## ◈ Keyword Themes

The dashboard ships with four pre-configured intelligence themes. All are editable in the sidebar.

```
Security & Crime ···· narcotráfico · cocaína · homicidio · violencia
                       sicario · masacre · Los Choneros · Lobos · Fito

Political ··········· Noboa · gobierno · asamblea · estado de excepción
                       elecciones · decreto · correísmo

Humanitarian ········ desplazado · refugiado · derechos humanos
                       indígena · ACNUR · CICR · migración

Economic ············ petróleo · exportación · puerto · Guayaquil
                       Posorja · FMI · dolarización
```

---

## ◈ Severity Model

Articles are automatically tagged using keyword presence in title and summary:

| Level | Triggers | Display |
|-------|----------|---------|
| 🔴 **High** | masacre · asesinato · homicidio · bomba · tortura · ejecución · desaparecido | Red |
| 🟡 **Medium** | violencia · narcotráfico · extorsión · protesta · desplazado · represión | Amber |
| 🟢 **Low** | Everything else | Green |

---

## ◈ Data Sources & Ethics

> This tool is built on the principle that effective human rights monitoring does not require illegal data collection.

**What this dashboard uses:**
- ✅ Public RSS feeds (openly published by each outlet)
- ✅ NewsAPI (licensed aggregation service)
- ✅ ACLED (designed specifically for conflict research, free for NGOs)

**What this dashboard does NOT do:**
- ❌ Social media scraping
- ❌ Scraping behind paywalls or login walls
- ❌ MILINT or classified sources
- ❌ Personal data collection of any kind

All content remains the copyright of its original publishers. This tool indexes and links; it does not republish full articles.

---

## ◈ Requirements

```
streamlit >= 1.32.0
pandas >= 2.0.0
feedparser >= 6.0.0
requests >= 2.31.0
folium >= 0.16.0
streamlit-folium >= 0.20.0
textblob >= 0.18.0
spacy >= 3.7.0, < 3.8.0
plotly >= 5.20.0
es-core-news-sm (installed via wheel in requirements.txt)
```

Python 3.10+ required. Tested on Python 3.11 and 3.13.

---

## ◈ Roadmap

- [ ] ACLED fatality trend chart
- [ ] Telegram daily digest bot integration
- [ ] Article clustering by topic (unsupervised)
- [ ] Alert thresholds — email/webhook when High severity spikes
- [ ] Multi-country expansion (Colombia, Peru border regions)
- [ ] Translation layer for non-Spanish feeds

---

## ◈ Disclaimer

This dashboard is intended for **educational and research purposes only**.

All data is sourced from publicly available, openly licensed news feeds and APIs. Users are responsible for complying with the terms of service of each data provider. Verify all incidents through primary sources before any operational use. This tool does not constitute legal, medical, or security advice.

---

<div align="center">

**Ecuador OSINT Dashboard** · NGO / Human Rights Edition · v3.0

Made with 🖤 for the people doing difficult work in difficult places.

`PUBLIC SOURCES ONLY · NO SOCIAL MEDIA SCRAPING · EDUCATIONAL USE`

</div>
