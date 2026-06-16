"""Parser fixture tests for Qwant engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "qwant"


class MockResponse:
    def __init__(self, text: str, url: str = "https://api.qwant.com/v3/search/web?", status_code: int = 200):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.search_params = {}


@pytest.fixture
def qwant():
    return load_engine("qwant")


class TestQwantParser:
    def test_web_api_returns_results(self, qwant):
        # qwant_categ must be "web" for web API parsing
        qwant.qwant_categ = "web"
        data = json.loads((FIXTURES_DIR / "success_web.json").read_text())
        resp = MockResponse(json.dumps(data))
        results = qwant.response(resp)
        assert len(results) >= 1

    def test_web_api_result_has_url(self, qwant):
        qwant.qwant_categ = "web"
        data = json.loads((FIXTURES_DIR / "success_web.json").read_text())
        resp = MockResponse(json.dumps(data))
        results = qwant.response(resp)
        for r in results:
            assert r["url"], "Result missing url"
            assert r["url"].startswith("http"), f"Invalid URL: {r['url']}"

    def test_web_api_result_has_title(self, qwant):
        qwant.qwant_categ = "web"
        data = json.loads((FIXTURES_DIR / "success_web.json").read_text())
        resp = MockResponse(json.dumps(data))
        results = qwant.response(resp)
        for r in results:
            assert r["title"], "Result missing title"

    def test_web_api_result_has_content(self, qwant):
        qwant.qwant_categ = "web"
        data = json.loads((FIXTURES_DIR / "success_web.json").read_text())
        resp = MockResponse(json.dumps(data))
        results = qwant.response(resp)
        assert any(r.get("content") for r in results), "No result has content"

    def test_error_status_raises(self, qwant):
        qwant.qwant_categ = "web"
        error_data = {"status": "error", "data": {"error_code": 24, "message": ["rate limited"]}}
        resp = MockResponse(json.dumps(error_data))
        from scoutlet.exceptions import SearchEngineTooManyRequestsException
        with pytest.raises(SearchEngineTooManyRequestsException):
            qwant.response(resp)
