"""Parser fixture tests for GitHub engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "github"


class MockResponse:
    def __init__(self, text: str, url: str = "https://api.github.com/search/repositories?q=test"):
        self.text = text
        self.url = url
        self.status_code = 200
        self.search_params = {}

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def github():
    return load_engine("github")


class TestGitHubParser:
    def test_success_returns_results(self, github):
        data = (FIXTURES_DIR / "success_repos.json").read_text()
        resp = MockResponse(data)
        results = github.response(resp)
        assert len(results) >= 1

    def test_result_has_url(self, github):
        data = (FIXTURES_DIR / "success_repos.json").read_text()
        resp = MockResponse(data)
        results = github.response(resp)
        for r in results:
            assert r["url"], "Result missing url"
            assert r["url"].startswith("https://github.com"), f"Invalid URL: {r['url']}"

    def test_result_has_title(self, github):
        data = (FIXTURES_DIR / "success_repos.json").read_text()
        resp = MockResponse(data)
        results = github.response(resp)
        for r in results:
            assert r["title"], "Result missing title"

    def test_result_has_content(self, github):
        data = (FIXTURES_DIR / "success_repos.json").read_text()
        resp = MockResponse(data)
        results = github.response(resp)
        assert any(r.get("content") for r in results), "No result has content"

    def test_result_has_published_date(self, github):
        data = (FIXTURES_DIR / "success_repos.json").read_text()
        resp = MockResponse(data)
        results = github.response(resp)
        assert any(r.get("publishedDate") for r in results), "No result has publishedDate"
