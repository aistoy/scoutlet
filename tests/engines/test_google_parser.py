"""Parser fixture tests for Google engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine
from scoutlet.exceptions import SearchEngineCaptchaException

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "google"


class MockResponse:
    def __init__(self, text: str, url: str = "https://www.google.com/search?q=test"):
        self.text = text
        self.url = url
        self.status_code = 200
        self.search_params = {}


@pytest.fixture
def google():
    return load_engine("google")


class TestGoogleParser:
    def test_success_returns_results(self, google):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = google.response(resp)
        assert len(results) >= 1

    def test_result_has_url(self, google):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = google.response(resp)
        for r in results:
            if "url" in r:
                assert r["url"], "Result missing url"
                assert r["url"].startswith("http"), f"Invalid URL: {r['url']}"

    def test_result_has_title(self, google):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = google.response(resp)
        titled_results = [r for r in results if "title" in r]
        assert len(titled_results) >= 1, "No results with title"
        for r in titled_results:
            assert r["title"], "Result has empty title"
