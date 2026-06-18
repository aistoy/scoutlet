"""Parser fixture tests for Yahoo engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "yahoo"


class MockResponse:
    def __init__(self, text, url="https://search.yahoo.com/search", status_code=200,
                 domain="search.yahoo.com"):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.search_params = {"domain": domain}


@pytest.fixture
def yahoo():
    return load_engine("yahoo")


class TestYahooParser:
    def test_parses_results_from_live_html(self, yahoo):
        html = (FIXTURES_DIR / "python_asyncio.html").read_text()
        results = yahoo.response(MockResponse(html))
        assert len(results) >= 5

    def test_every_result_has_url_and_title(self, yahoo):
        """Regression: yahoo used to emit {'suggestion': ...} dicts that
        became ghost SearchResults with empty url/title but non-zero score.
        Every dict returned must have url and title populated.
        """
        html = (FIXTURES_DIR / "python_asyncio.html").read_text()
        results = yahoo.response(MockResponse(html))
        assert results, "fixture should yield at least one result"
        for r in results:
            assert r.get("url"), f"result missing url: {r!r}"
            assert r.get("title"), f"result missing title: {r!r}"

    def test_first_result_shape(self, yahoo):
        html = (FIXTURES_DIR / "python_asyncio.html").read_text()
        results = yahoo.response(MockResponse(html))
        first = results[0]
        assert set(first.keys()) >= {"url", "title", "content"}
        assert first["url"].startswith("http")
