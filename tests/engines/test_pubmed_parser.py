"""Parser fixture tests for PubMed engine (response() only — request() does sync HTTP)."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "pubmed"


class MockResponse:
    def __init__(self, content: bytes, url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"):
        self.content = content
        self.text = content.decode("utf-8")
        self.url = url
        self.status_code = 200


@pytest.fixture
def pubmed():
    return load_engine("pubmed")


class TestPubMedParser:
    def test_returns_results(self, pubmed):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = pubmed.response(MockResponse(xml))
        assert len(results) == 2

    def test_pubmed_url(self, pubmed):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = pubmed.response(MockResponse(xml))
        assert results[0]["url"] == "https://www.ncbi.nlm.nih.gov/pubmed/12345678"

    def test_title_extracted(self, pubmed):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = pubmed.response(MockResponse(xml))
        assert results[0]["title"] == "CRISPR-Cas9 genome editing"

    def test_authors(self, pubmed):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = pubmed.response(MockResponse(xml))
        assert "Jennifer Doudna" in results[0]["authors"]
        assert "Emmanuelle Charpentier" in results[0]["authors"]

    def test_doi_extracted(self, pubmed):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = pubmed.response(MockResponse(xml))
        assert results[0]["doi"] == "10.1038/nature12345"

    def test_journal_extracted(self, pubmed):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = pubmed.response(MockResponse(xml))
        assert results[0]["journal"] == "Nature"

    def test_published_date_from_accepted(self, pubmed):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = pubmed.response(MockResponse(xml))
        assert results[0]["publishedDate"].year == 2014
        assert results[0]["publishedDate"].month == 6

    def test_missing_published_date(self, pubmed):
        # Second entry has no accepted date
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = pubmed.response(MockResponse(xml))
        assert results[1]["publishedDate"] is None
