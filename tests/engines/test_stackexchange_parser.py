"""Parser fixture tests for Stack Exchange engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "stackexchange"


class MockResponse:
    def __init__(self, text: str, url: str = "https://api.stackexchange.com/2.3/search/advanced?q=test"):
        self.text = text
        self.url = url
        self.status_code = 200
        self.search_params = {}


@pytest.fixture
def se():
    return load_engine("stackexchange")


class TestStackExchangeParser:
    def test_success_returns_results(self, se):
        data = (FIXTURES_DIR / "success_questions.json").read_text()
        resp = MockResponse(data)
        results = se.response(resp)
        assert len(results) >= 1

    def test_result_has_url(self, se):
        data = (FIXTURES_DIR / "success_questions.json").read_text()
        resp = MockResponse(data)
        results = se.response(resp)
        for r in results:
            assert r["url"], "Result missing url"
            assert "stackoverflow.com/q/" in r["url"]

    def test_result_has_title(self, se):
        data = (FIXTURES_DIR / "success_questions.json").read_text()
        resp = MockResponse(data)
        results = se.response(resp)
        for r in results:
            assert r["title"], "Result missing title"

    def test_result_has_content(self, se):
        data = (FIXTURES_DIR / "success_questions.json").read_text()
        resp = MockResponse(data)
        results = se.response(resp)
        for r in results:
            assert r["content"], "Result missing content"
            assert "python" in r["content"].lower() or "score" in r["content"]
