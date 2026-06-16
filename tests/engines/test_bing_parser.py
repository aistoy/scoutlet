"""Parser fixture tests for Bing engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "bing"


class MockResponse:
    def __init__(self, text: str, url: str = "https://www.bing.com/search?q=test"):
        self.text = text
        self.url = url
        self.status_code = 200
        self.search_params = {}


@pytest.fixture
def bing():
    return load_engine("bing")


class TestBingParser:
    def test_success_returns_results(self, bing):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing.response(resp)
        assert len(results) >= 1

    def test_result_has_url(self, bing):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing.response(resp)
        for r in results:
            assert r["url"], "Result missing url"
            assert r["url"].startswith("http"), f"Invalid URL: {r['url']}"

    def test_result_has_title(self, bing):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing.response(resp)
        for r in results:
            assert r["title"], "Result missing title"

    def test_result_has_content(self, bing):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing.response(resp)
        assert any(r.get("content") for r in results), "No result has content"

    def test_captcha_page_detected(self, bing):
        html = (FIXTURES_DIR / "captcha_minimal.html").read_text()
        resp = MockResponse(html)
        # Bing parser doesn't auto-raise on captcha HTML, but should return empty
        results = bing.response(resp)
        # With a captcha page, the parser shouldn't find real results
        assert len(results) == 0 or all(not r.get("url") for r in results)
