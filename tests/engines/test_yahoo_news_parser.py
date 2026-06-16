"""Parser fixture tests for Yahoo News engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "yahoo_news"


class MockResponse:
    def __init__(self, text, url="https://news.search.yahoo.com/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def yahoo_news():
    return load_engine("yahoo_news")


class TestYahooNewsParser:
    def test_returns_results_with_suggestions(self, yahoo_news):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = yahoo_news.response(MockResponse(html))
        # 2 news items + 2 suggestions
        assert len(results) == 4

    def test_url_decoded_from_redir(self, yahoo_news):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = yahoo_news.response(MockResponse(html))
        assert results[0]["url"].startswith("https://example.com/news1")

    def test_title(self, yahoo_news):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = yahoo_news.response(MockResponse(html))
        assert results[0]["title"] == "Breaking News Title"

    def test_ago_relative_date(self, yahoo_news):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = yahoo_news.response(MockResponse(html))
        # "2 hours ago" should produce a publishedDate
        assert results[0]["publishedDate"] is not None
