"""Parser fixture tests for DuckDuckGo engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine
from scoutlet.exceptions import SearchEngineCaptchaException

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "duckduckgo"


class MockResponse:
    def __init__(self, text: str, url: str = "https://html.duckduckgo.com/html/", status_code: int = 200):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.search_params = {}


@pytest.fixture
def ddg():
    return load_engine("duckduckgo")


class TestDuckDuckGoParser:
    def test_success_returns_results(self, ddg):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = ddg.response(resp)
        assert len(results) >= 1

    def test_result_has_url(self, ddg):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = ddg.response(resp)
        for r in results:
            assert r["url"], "Result missing url"
            assert r["url"].startswith("http"), f"Invalid URL: {r['url']}"

    def test_result_has_title(self, ddg):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = ddg.response(resp)
        assert any(r.get("title") for r in results), "No result has title"

    def test_captcha_raises(self, ddg):
        html = (FIXTURES_DIR / "captcha_minimal.html").read_text()
        resp = MockResponse(html)
        with pytest.raises(SearchEngineCaptchaException):
            ddg.response(resp)

    def test_303_returns_empty(self, ddg):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html, status_code=303)
        results = ddg.response(resp)
        assert len(results) == 0
