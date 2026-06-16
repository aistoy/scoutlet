"""Parser fixture tests for INA engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "ina"


class MockResponse:
    def __init__(self, text, url="https://www.ina.fr/ajax/recherche"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def ina():
    return load_engine("ina")


class TestInaParser:
    def test_returns_results(self, ina):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ina.response(MockResponse(html))
        assert len(results) == 2

    def test_url(self, ina):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ina.response(MockResponse(html))
        assert results[0]["url"] == "https://www.ina.fr/video/12345"

    def test_title(self, ina):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ina.response(MockResponse(html))
        assert results[0]["title"] == "Inauguration Speech"

    def test_thumbnail(self, ina):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ina.response(MockResponse(html))
        assert results[0]["thumbnail"] == "https://example.com/thumb1.jpg"

    def test_content_combines_date_and_subtitle(self, ina):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ina.response(MockResponse(html))
        assert "1981-05-21" in results[0]["content"]
        assert "Politics" in results[0]["content"]
