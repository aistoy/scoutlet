"""Parser fixture tests for Baidu engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "baidu"


class MockResponse:
    def __init__(self, text: str, url: str = "https://www.baidu.com/s?wd=test", status_code: int = 200):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.headers = {}
        self.search_params = {}


@pytest.fixture
def baidu():
    return load_engine("baidu")


class TestBaiduParser:
    def test_general_returns_results(self, baidu):
        baidu.baidu_category = "general"
        data = json.loads((FIXTURES_DIR / "success_general.json").read_text())
        resp = MockResponse(json.dumps(data))
        results = baidu.response(resp)
        assert len(results) >= 1

    def test_general_result_has_url(self, baidu):
        baidu.baidu_category = "general"
        data = json.loads((FIXTURES_DIR / "success_general.json").read_text())
        resp = MockResponse(json.dumps(data))
        results = baidu.response(resp)
        for r in results:
            assert r["url"], "Result missing url"
            assert r["url"].startswith("http"), f"Invalid URL: {r['url']}"

    def test_general_result_has_title(self, baidu):
        baidu.baidu_category = "general"
        data = json.loads((FIXTURES_DIR / "success_general.json").read_text())
        resp = MockResponse(json.dumps(data))
        results = baidu.response(resp)
        for r in results:
            assert r["title"], "Result missing title"

    def test_general_result_has_content(self, baidu):
        baidu.baidu_category = "general"
        data = json.loads((FIXTURES_DIR / "success_general.json").read_text())
        resp = MockResponse(json.dumps(data))
        results = baidu.response(resp)
        assert any(r.get("content") for r in results), "No result has content"
