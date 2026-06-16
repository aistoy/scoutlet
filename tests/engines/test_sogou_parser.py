"""Parser fixture tests for Sogou engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "sogou"


class MockResponse:
    def __init__(self, text: str, url: str = "https://www.sogou.com/web?query=test"):
        self.text = text
        self.url = url
        self.status_code = 200
        self.search_params = {}


@pytest.fixture
def sogou():
    return load_engine("sogou")


class TestSogouParser:
    def test_success_returns_results(self, sogou):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = sogou.response(resp)
        assert len(results) >= 1

    def test_result_has_url(self, sogou):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = sogou.response(resp)
        for r in results:
            assert r["url"], "Result missing url"
            assert r["url"].startswith("http"), f"Invalid URL: {r['url']}"

    def test_result_has_title(self, sogou):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = sogou.response(resp)
        for r in results:
            assert r["title"], "Result missing title"
