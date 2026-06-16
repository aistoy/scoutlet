"""Parser fixture tests for Crossref engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "crossref"


class MockResponse:
    def __init__(self, text: str, url: str = "https://api.crossref.org/works"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def crossref():
    return load_engine("crossref")


class TestCrossrefParser:
    def test_returns_results_skipping_components(self, crossref):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = crossref.response(MockResponse(data))
        # 2 valid items + 1 component-type that's skipped
        assert len(results) == 2

    def test_result_url(self, crossref):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = crossref.response(MockResponse(data))
        assert results[0]["url"] == "https://doi.org/10.1000/test1"

    def test_journal_article_title(self, crossref):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = crossref.response(MockResponse(data))
        assert results[0]["title"] == "Attention Is All You Need"
        assert results[0]["journal"] == "NeurIPS Proceedings"

    def test_book_chapter_title(self, crossref):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = crossref.response(MockResponse(data))
        # Second result is book-chapter
        assert "Deep Learning Book" in results[1]["title"]

    def test_published_date_full(self, crossref):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = crossref.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2017
        assert results[0]["publishedDate"].month == 6

    def test_published_date_year_only(self, crossref):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = crossref.response(MockResponse(data))
        # book-chapter has year-only date-parts
        assert results[1]["publishedDate"].year == 2016

    def test_authors_parsed(self, crossref):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = crossref.response(MockResponse(data))
        assert "Ashish Vaswani" in results[0]["authors"]
        assert "Noam Shazeer" in results[0]["authors"]

    def test_doi_field(self, crossref):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = crossref.response(MockResponse(data))
        assert results[0]["doi"] == "10.1000/test1"

    def test_request_paging(self, crossref):
        params = {"pageno": 2}
        crossref.request("transformer", params)
        assert "offset=20" in params["url"]
