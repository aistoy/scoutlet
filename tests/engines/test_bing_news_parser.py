"""Parser fixture tests for Bing News engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "bing_news"


class MockResponse:
    def __init__(self, text: str, url: str = "https://www.bing.com/news/search?q=test"):
        self.text = text
        self.url = url
        self.status_code = 200
        self.search_params = {}


@pytest.fixture
def bing_news():
    return load_engine("bing_news")


class TestBingNewsParser:
    def test_success_returns_results(self, bing_news):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing_news.response(resp)
        assert len(results) >= 1

    def test_result_has_url(self, bing_news):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing_news.response(resp)
        for r in results:
            assert r["url"], "Result missing url"
            assert r["url"].startswith("http"), f"Invalid URL: {r['url']}"

    def test_result_has_title(self, bing_news):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing_news.response(resp)
        for r in results:
            assert r["title"], "Result missing title"
