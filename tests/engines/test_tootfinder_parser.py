"""Parser fixture tests for Tootfinder engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "tootfinder"


class MockResponse:
    def __init__(self, text, url="https://www.tootfinder.ch/rest/api/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def tootfinder():
    return load_engine("tootfinder")


class TestTootfinderParser:
    def test_returns_results(self, tootfinder):
        text = (FIXTURES_DIR / "success.txt").read_text()
        results = tootfinder.response(MockResponse(text))
        assert len(results) == 2

    def test_url(self, tootfinder):
        text = (FIXTURES_DIR / "success.txt").read_text()
        results = tootfinder.response(MockResponse(text))
        assert results[0]["url"] == "https://mastodon.social/@user/12345"

    def test_title_from_card(self, tootfinder):
        text = (FIXTURES_DIR / "success.txt").read_text()
        results = tootfinder.response(MockResponse(text))
        assert results[0]["title"] == "A great post"
        # No card on second - falls back to content snippet
        assert "Another toot" in results[1]["title"]

    def test_thumbnail_from_first_image(self, tootfinder):
        text = (FIXTURES_DIR / "success.txt").read_text()
        results = tootfinder.response(MockResponse(text))
        assert results[0]["thumbnail"] == "https://example.com/preview.jpg"
        assert results[1]["thumbnail"] is None

    def test_html_stripped_from_content(self, tootfinder):
        text = (FIXTURES_DIR / "success.txt").read_text()
        results = tootfinder.response(MockResponse(text))
        assert "<p>" not in results[0]["content"]
        assert "Hello" in results[0]["content"]

    def test_published_date(self, tootfinder):
        text = (FIXTURES_DIR / "success.txt").read_text()
        results = tootfinder.response(MockResponse(text))
        assert results[0]["publishedDate"].year == 2024
