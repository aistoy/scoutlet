"""Parser fixture tests for OpenAlex engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "openalex"


class MockResponse:
    def __init__(self, text: str, url: str = "https://api.openalex.org/works"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def openalex():
    return load_engine("openalex")


class TestOpenAlexParser:
    def test_returns_results(self, openalex):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openalex.response(MockResponse(data))
        assert len(results) == 1

    def test_landing_page_url(self, openalex):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openalex.response(MockResponse(data))
        assert results[0]["url"] == "https://arxiv.org/abs/1706.03762"

    def test_abstract_reconstructed_from_inverted_index(self, openalex):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openalex.response(MockResponse(data))
        content = results[0]["content"]
        assert content.startswith("The dominant sequence transduction")

    def test_doi_stripped(self, openalex):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openalex.response(MockResponse(data))
        assert results[0]["doi"] == "10.48550/arXiv.1706.03762"

    def test_authors_extracted(self, openalex):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openalex.response(MockResponse(data))
        assert "Ashish Vaswani" in results[0]["authors"]

    def test_published_date_parsed(self, openalex):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openalex.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2017

    def test_citations_in_content(self, openalex):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openalex.response(MockResponse(data))
        assert "100000 citations" in results[0]["content"]

    def test_request_basic(self, openalex):
        params = {"pageno": 1, "headers": {}}
        openalex.request("transformer", params)
        assert "search=transformer" in params["url"]
        assert "sort=relevance_score" in params["url"]

    def test_request_language_filter(self, openalex):
        params = {"pageno": 1, "headers": {}, "language": "en-US"}
        openalex.request("test", params)
        assert "filter=language" in params["url"]
