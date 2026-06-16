"""Parser fixture tests for Radio Browser engine (response() only)."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "radio_browser"


class MockResponse:
    def __init__(self, text, url="https://de1.api.radio-browser.info/json/stations/search"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def radio_browser():
    return load_engine("radio_browser")


class TestRadioBrowserParser:
    def test_returns_results(self, radio_browser):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = radio_browser.response(MockResponse(data))
        assert len(results) == 2

    def test_url_prefers_homepage(self, radio_browser):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = radio_browser.response(MockResponse(data))
        assert results[0]["url"] == "https://example.com"

    def test_url_fallback_to_stream(self, radio_browser):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = radio_browser.response(MockResponse(data))
        # Second has empty homepage
        assert results[1]["url"] == "https://stream.jazz.fm/live"

    def test_thumbnail_upgraded_to_https(self, radio_browser):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = radio_browser.response(MockResponse(data))
        assert results[0]["thumbnail"].startswith("https://")

    def test_metadata_skips_unknown_codec(self, radio_browser):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = radio_browser.response(MockResponse(data))
        # First has MP3 codec, second has "unknown"
        assert "MP3 radio" in results[0]["metadata"]
        assert "radio" not in results[1]["metadata"].split("bitrate")[0]

    def test_iframe_uses_https_stream(self, radio_browser):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = radio_browser.response(MockResponse(data))
        assert results[0]["iframe_src"].startswith("https://")
