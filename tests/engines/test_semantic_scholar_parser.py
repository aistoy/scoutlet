"""Parser fixture tests for Semantic Scholar engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "semantic_scholar"


class MockResponse:
    def __init__(self, text: str, url: str = "https://www.semanticscholar.org/api/1/search"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def semantic_scholar():
    return load_engine("semantic_scholar")


class TestSemanticScholarParser:
    def test_returns_results(self, semantic_scholar):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = semantic_scholar.response(MockResponse(data))
        assert len(results) == 2

    def test_primary_paper_link_url(self, semantic_scholar):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = semantic_scholar.response(MockResponse(data))
        assert results[0]["url"] == "https://arxiv.org/abs/1706.03762"

    def test_title_from_dict(self, semantic_scholar):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = semantic_scholar.response(MockResponse(data))
        assert results[0]["title"] == "Attention Is All You Need"

    def test_abstract_html_stripped(self, semantic_scholar):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = semantic_scholar.response(MockResponse(data))
        assert "dominant sequence transduction" in results[0]["content"]

    def test_authors_extracted(self, semantic_scholar):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = semantic_scholar.response(MockResponse(data))
        assert "Ashish Vaswani" in results[0]["authors"]
        assert len(results[0]["authors"]) == 2

    def test_pdf_url_skips_crawler(self, semantic_scholar):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = semantic_scholar.response(MockResponse(data))
        # crawler is skipped, pdf link wins
        assert results[0]["pdf_url"] == "https://arxiv.org/pdf/1706.03762"

    def test_published_date(self, semantic_scholar):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = semantic_scholar.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2017

    def test_fallback_url_for_minimal_record(self, semantic_scholar):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = semantic_scholar.response(MockResponse(data))
        # Second result has no primaryPaperLink/links/alternatePaperLinks
        assert results[1]["url"].startswith("https://www.semanticscholar.org/paper/")

    def test_request_uses_post_json(self, semantic_scholar):
        params = {"pageno": 2, "headers": {}}
        semantic_scholar.request("test query", params)
        assert params["method"] == "POST"
        assert "Content-Type" in params["headers"]
        assert params["json"]["queryString"] == "test query"
        assert params["json"]["page"] == 2
