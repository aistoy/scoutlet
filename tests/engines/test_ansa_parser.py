"""Parser fixture tests for Ansa engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "ansa"


class MockResponse:
    def __init__(self, text, url="https://www.ansa.it/ricerca/ansait/search.shtml"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def ansa():
    return load_engine("ansa")


class TestAnsaParser:
    def test_returns_results(self, ansa):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ansa.response(MockResponse(html))
        assert len(results) == 2

    def test_url(self, ansa):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ansa.response(MockResponse(html))
        assert results[0]["url"] == "https://www.ansa.it/news/12345"

    def test_title(self, ansa):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ansa.response(MockResponse(html))
        assert results[0]["title"] == "Elezioni, le ultime notizie"

    def test_thumbnail_optional(self, ansa):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ansa.response(MockResponse(html))
        assert results[0]["thumbnail"].endswith("/images/news1.jpg")
        assert "thumbnail" not in results[1] or not results[1].get("thumbnail")
