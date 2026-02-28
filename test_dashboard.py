"""
Tests for Ecuador OSINT Dashboard — pure functions and constants.

Run:  pytest test_dashboard.py -v
"""

import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ── Mock Streamlit before importing the dashboard module ─────────────────────
# The dashboard calls st.set_page_config, st.markdown, etc. at import time,
# so we need Streamlit mocked before the first import.

_mock_st = MagicMock()
_mock_st.secrets = {}
_mock_st.cache_data = lambda **kw: (lambda fn: fn)  # passthrough decorator

# Sidebar widgets return sensible defaults so module-level code can execute
_mock_st.text_input.return_value = ""
_mock_st.slider.return_value = 14
_mock_st.multiselect.return_value = []
_mock_st.number_input.return_value = 3
_mock_st.sidebar.__enter__ = lambda s: _mock_st
_mock_st.sidebar.__exit__ = MagicMock(return_value=False)
_mock_st.spinner.__enter__ = MagicMock(return_value=None)
_mock_st.spinner.__exit__ = MagicMock(return_value=False)

# st.tabs returns 8 context-manager mocks (one per tab)
_tab_mocks = [MagicMock() for _ in range(8)]
for _t in _tab_mocks:
    _t.__enter__ = lambda s: s
    _t.__exit__ = MagicMock(return_value=False)
_mock_st.tabs.return_value = _tab_mocks

# Mock requests so no HTTP calls happen on import
_mock_requests = MagicMock()
_mock_feedparser = MagicMock()
_mock_feedparser.parse.return_value = MagicMock(entries=[], feed=MagicMock())

sys.modules["streamlit"] = _mock_st
sys.modules["streamlit_folium"] = MagicMock()
sys.modules["folium"] = MagicMock()
sys.modules["feedparser"] = _mock_feedparser
sys.modules["requests"] = _mock_requests
sys.modules["plotly"] = MagicMock()
sys.modules["plotly.express"] = MagicMock()
sys.modules["plotly.graph_objects"] = MagicMock()

import ecuador_osint_v2 as dash  # noqa: E402


# ═════════════════════════════════════════════════════════════════════════════
# CONSTANT / DATA-STRUCTURE VALIDATION
# ═════════════════════════════════════════════════════════════════════════════


class TestSources:
    def test_sources_not_empty(self):
        assert len(dash.SOURCES) > 0

    def test_all_urls_are_strings(self):
        for name, url in dash.SOURCES.items():
            assert isinstance(url, str), f"{name} URL is not a string"
            assert url.startswith("http"), f"{name} URL does not start with http"

    def test_no_empty_keys_or_values(self):
        for name, url in dash.SOURCES.items():
            assert name.strip(), "Empty source name"
            assert url.strip(), f"Empty URL for {name}"


class TestKeywordThemes:
    def test_expected_themes_exist(self):
        expected = {"Security & Crime", "Political", "Humanitarian", "Economic"}
        assert expected == set(dash.KEYWORD_THEMES.keys())

    def test_each_theme_has_keywords(self):
        for theme, kws in dash.KEYWORD_THEMES.items():
            assert len(kws) >= 5, f"Theme '{theme}' has fewer than 5 keywords"

    def test_no_empty_keywords(self):
        for theme, kws in dash.KEYWORD_THEMES.items():
            for kw in kws:
                assert kw.strip(), f"Empty keyword in theme '{theme}'"


class TestSeverityKeywords:
    def test_high_severity_not_empty(self):
        assert len(dash.HIGH_SEVERITY) > 0

    def test_medium_severity_not_empty(self):
        assert len(dash.MEDIUM_SEVERITY) > 0

    def test_all_high_are_lowercase(self):
        for w in dash.HIGH_SEVERITY:
            assert w == w.lower(), f"HIGH_SEVERITY word '{w}' is not lowercase"

    def test_all_medium_are_lowercase(self):
        for w in dash.MEDIUM_SEVERITY:
            assert w == w.lower(), f"MEDIUM_SEVERITY word '{w}' is not lowercase"

    def test_no_overlap_between_high_and_medium(self):
        overlap = dash.HIGH_SEVERITY & dash.MEDIUM_SEVERITY
        assert not overlap, f"Overlap between HIGH and MEDIUM severity: {overlap}"


class TestLocationCoords:
    def test_not_empty(self):
        assert len(dash.LOCATION_COORDS) > 0

    def test_keys_are_lowercase(self):
        for loc in dash.LOCATION_COORDS:
            assert loc == loc.lower(), f"Location key '{loc}' is not lowercase"

    def test_valid_lat_lon(self):
        for loc, (lat, lon) in dash.LOCATION_COORDS.items():
            assert -90 <= lat <= 90, f"{loc}: latitude {lat} out of range"
            assert -180 <= lon <= 180, f"{loc}: longitude {lon} out of range"

    def test_ecuador_cities_in_plausible_bounds(self):
        ecuador_cities = [
            "guayaquil", "quito", "esmeraldas", "manta", "cuenca",
            "portoviejo", "machala", "loja", "ambato", "posorja",
        ]
        for city in ecuador_cities:
            lat, lon = dash.LOCATION_COORDS[city]
            assert -5.5 <= lat <= 2.0, f"{city} lat {lat} not in Ecuador"
            assert -82 <= lon <= -75, f"{city} lon {lon} not in Ecuador"


# ═════════════════════════════════════════════════════════════════════════════
# PURE FUNCTION TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestComputeSeverity:
    def test_high_severity_in_title(self):
        assert dash.compute_severity("Masacre en Guayaquil", "") == "🔴 High"

    def test_high_severity_in_summary(self):
        assert dash.compute_severity("Noticia", "un asesinato reportado") == "🔴 High"

    def test_medium_severity(self):
        assert dash.compute_severity("Extorsión en la costa", "") == "🟡 Medium"

    def test_low_severity(self):
        assert dash.compute_severity("Reunión de comercio", "exportación crece") == "🟢 Low"

    def test_empty_strings_return_low(self):
        assert dash.compute_severity("", "") == "🟢 Low"

    def test_high_takes_precedence_over_medium(self):
        result = dash.compute_severity("violencia y masacre", "narcotráfico")
        assert result == "🔴 High"

    def test_case_insensitive(self):
        assert dash.compute_severity("HOMICIDIO reportado", "") == "🔴 High"


class TestComputeSentiment:
    def test_returns_tuple(self):
        label, score = dash.compute_sentiment("good great excellent")
        assert isinstance(label, str)
        assert isinstance(score, float)

    def test_label_is_valid(self):
        label, _ = dash.compute_sentiment("something")
        assert label in ("Positive", "Negative", "Neutral")

    def test_empty_string(self):
        label, score = dash.compute_sentiment("")
        assert label == "Neutral"
        assert score == 0.0

    def test_score_rounded_to_3_decimals(self):
        _, score = dash.compute_sentiment("This is wonderful and amazing")
        assert score == round(score, 3)


class TestTagThemes:
    def test_security_theme_detected(self):
        themes = dash.tag_themes("narcotráfico en la frontera", "")
        assert "Security & Crime" in themes

    def test_political_theme_detected(self):
        themes = dash.tag_themes("Noboa anuncia decreto", "")
        assert "Political" in themes

    def test_humanitarian_theme_detected(self):
        themes = dash.tag_themes("", "derechos humanos vulnerados")
        assert "Humanitarian" in themes

    def test_economic_theme_detected(self):
        themes = dash.tag_themes("exportación de petróleo", "")
        assert "Economic" in themes

    def test_multiple_themes(self):
        themes = dash.tag_themes("narcotráfico y Noboa", "derechos humanos")
        assert len(themes) >= 3

    def test_no_match_returns_empty(self):
        themes = dash.tag_themes("hello world", "test")
        assert themes == []

    def test_case_insensitive(self):
        themes = dash.tag_themes("NARCOTRÁFICO", "")
        assert "Security & Crime" in themes


class TestKeywordMatch:
    def test_empty_keywords_returns_true(self):
        row = {"Title": "anything", "Summary": "anything"}
        assert dash.keyword_match(row, []) is True

    def test_keyword_in_title(self):
        row = {"Title": "Violencia en Ecuador", "Summary": ""}
        assert dash.keyword_match(row, ["violencia"]) is True

    def test_keyword_in_summary(self):
        row = {"Title": "", "Summary": "protesta estudiantil"}
        assert dash.keyword_match(row, ["protesta"]) is True

    def test_no_match(self):
        row = {"Title": "Good morning", "Summary": "Weather is fine"}
        assert dash.keyword_match(row, ["masacre"]) is False

    def test_case_insensitive(self):
        row = {"Title": "VIOLENCIA reportada", "Summary": ""}
        assert dash.keyword_match(row, ["violencia"]) is True


class TestHighlight:
    def test_basic_highlight(self):
        result = dash.highlight("Violencia en Quito", ["violencia"])
        assert "**Violencia**" in result

    def test_case_insensitive(self):
        result = dash.highlight("QUITO es capital", ["quito"])
        assert "**QUITO**" in result

    def test_multiple_keywords(self):
        result = dash.highlight("Violencia en Quito", ["violencia", "quito"])
        assert "**Violencia**" in result
        assert "**Quito**" in result

    def test_empty_keywords(self):
        text = "No changes here"
        assert dash.highlight(text, []) == text

    def test_special_chars_in_keyword(self):
        result = dash.highlight("test (abc) end", ["(abc)"])
        assert "**(abc)**" in result


class TestDetectLocations:
    def test_single_location(self):
        result = dash.detect_locations("Incidente en Guayaquil hoy")
        assert len(result) == 1
        assert result[0][0] == "Guayaquil"

    def test_multiple_locations(self):
        result = dash.detect_locations("Quito y Guayaquil reportan problemas")
        names = [r[0] for r in result]
        assert "Quito" in names
        assert "Guayaquil" in names

    def test_no_locations(self):
        result = dash.detect_locations("Nothing here at all")
        assert result == []

    def test_case_insensitive(self):
        result = dash.detect_locations("ESMERALDAS provincia")
        assert len(result) >= 1
        assert result[0][0] == "Esmeraldas"

    def test_returns_valid_coords(self):
        result = dash.detect_locations("Evento en Cuenca")
        assert len(result) == 1
        _, lat, lon = result[0]
        assert -90 <= lat <= 90
        assert -180 <= lon <= 180


class TestGenerateBriefing:
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame([
            {
                "Title": "Masacre en zona rural",
                "Source": "El Universo",
                "Severity": "🔴 High",
                "Themes": ["Security & Crime"],
                "Published": "2026-02-28 10:00",
                "Link": "https://example.com/1",
            },
            {
                "Title": "Reunión diplomática",
                "Source": "Primicias",
                "Severity": "🟢 Low",
                "Themes": ["Political"],
                "Published": "2026-02-28 12:00",
                "Link": "https://example.com/2",
            },
        ])

    def test_returns_string(self, sample_df):
        result = dash.generate_briefing(sample_df, pd.DataFrame())
        assert isinstance(result, str)

    def test_contains_header(self, sample_df):
        result = dash.generate_briefing(sample_df, pd.DataFrame())
        assert "ECUADOR SITUATION REPORT" in result

    def test_contains_article_count(self, sample_df):
        result = dash.generate_briefing(sample_df, pd.DataFrame())
        assert "2 articles" in result

    def test_contains_high_severity_count(self, sample_df):
        result = dash.generate_briefing(sample_df, pd.DataFrame())
        assert "1 articles" in result or "1 article" in result

    def test_high_severity_incident_listed(self, sample_df):
        result = dash.generate_briefing(sample_df, pd.DataFrame())
        assert "Masacre en zona rural" in result

    def test_acled_section_when_data_present(self, sample_df):
        acled = pd.DataFrame([
            {"event_type": "Battles", "fatalities": "3"},
            {"event_type": "Riots", "fatalities": "1"},
        ])
        result = dash.generate_briefing(sample_df, acled)
        assert "ACLED" in result
        assert "2 events" in result

    def test_empty_df(self):
        empty_df = pd.DataFrame(columns=["Title", "Source", "Severity", "Themes", "Published", "Link"])
        result = dash.generate_briefing(empty_df, pd.DataFrame())
        assert "ECUADOR SITUATION REPORT" in result
        assert "0 articles" in result

    def test_methodology_section(self, sample_df):
        result = dash.generate_briefing(sample_df, pd.DataFrame())
        assert "METHODOLOGY" in result
