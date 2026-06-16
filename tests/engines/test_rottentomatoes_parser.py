"""Parser fixture tests for RottenTomatoes engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "rottentomatoes"


class MockResponse:
    def __init__(self, text, url="https://www.rottentomatoes.com/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def rottentomatoes():
    return load_engine("rottentomatoes")


class TestRottentomatoesParser:
    def test_returns_results(self, rottentomatoes):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = rottentomatoes.response(MockResponse(html))
        assert len(results) == 2

    def test_url(self, rottentomatoes):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = rottentomatoes.response(MockResponse(html))
        assert results[0]["url"] == "https://www.rottentomatoes.com/m/matrix"

    def test_title_from_alt(self, rottentomatoes):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = rottentomatoes.response(MockResponse(html))
        assert results[0]["title"] == "The Matrix"

    def test_content_includes_year_score_cast(self, rottentomatoes):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = rottentomatoes.response(MockResponse(html))
        content = results[0]["content"]
        assert "1999" in content
        assert "Score: 93" in content
        assert "Keanu Reeves" in content
