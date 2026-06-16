"""Parser fixture tests for arXiv engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "arxiv"


class MockResponse:
    def __init__(self, content: bytes, url: str = "https://export.arxiv.org/api/query"):
        self.content = content
        self.text = content.decode("utf-8")
        self.url = url
        self.status_code = 200


@pytest.fixture
def arxiv():
    return load_engine("arxiv")


class TestArxivParser:
    def test_returns_results(self, arxiv):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = arxiv.response(MockResponse(xml))
        assert len(results) == 2

    def test_result_has_url(self, arxiv):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = arxiv.response(MockResponse(xml))
        for r in results:
            assert r["url"].startswith("http://arxiv.org/abs/")

    def test_result_has_title(self, arxiv):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = arxiv.response(MockResponse(xml))
        titles = [r["title"] for r in results]
        assert "Attention Is All You Need" in titles

    def test_result_authors_parsed(self, arxiv):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = arxiv.response(MockResponse(xml))
        first = results[0]
        assert "Ashish Vaswani" in first["authors"]
        assert len(first["authors"]) == 2

    def test_result_published_date(self, arxiv):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = arxiv.response(MockResponse(xml))
        assert results[0]["publishedDate"] is not None
        assert results[0]["publishedDate"].year == 2017

    def test_result_has_pdf_url(self, arxiv):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = arxiv.response(MockResponse(xml))
        assert "/pdf/" in results[0]["pdf_url"]

    def test_request_builds_url(self, arxiv):
        params = {"pageno": 1, "headers": {}}
        arxiv.request("transformer", params)
        assert "search_query=all%3Atransformer" in params["url"]
        assert "max_results=10" in params["url"]
