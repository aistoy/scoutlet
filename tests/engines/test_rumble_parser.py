"""Parser fixture tests for Rumble engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "rumble"


class MockResponse:
    def __init__(self, text, url="https://rumble.com/search/video"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def rumble():
    return load_engine("rumble")


class TestRumbleParser:
    def test_returns_results(self, rumble):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = rumble.response(MockResponse(html))
        assert len(results) == 2

    def test_url(self, rumble):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = rumble.response(MockResponse(html))
        assert results[0]["url"] == "https://rumble.com/v1abc.html"

    def test_published_date_with_timezone(self, rumble):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = rumble.response(MockResponse(html))
        assert results[0]["publishedDate"].year == 2024

    def test_content_includes_views_rumbles_earned(self, rumble):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = rumble.response(MockResponse(html))
        assert "views" in results[0]["content"]
        assert "rumbles" in results[0]["content"]
        assert "$5.50" in results[0]["content"]

    def test_no_earned_falls_back_to_views_rumbles(self, rumble):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = rumble.response(MockResponse(html))
        # Second entry has empty earned
        assert "$" not in results[1]["content"]
