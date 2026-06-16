"""Parser fixture tests for SensCritique engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "senscritique"


class MockResponse:
    def __init__(self, text, url="https://apollo.senscritique.com/"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def senscritique():
    return load_engine("senscritique")


class TestSenscritiqueParser:
    def test_returns_results(self, senscritique):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = senscritique.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, senscritique):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = senscritique.response(MockResponse(data))
        assert results[0]["url"].endswith("/film/inception")

    def test_title_with_year(self, senscritique):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = senscritique.response(MockResponse(data))
        assert "Inception (2010)" == results[0]["title"]

    def test_content_includes_directors_genres_rating(self, senscritique):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = senscritique.response(MockResponse(data))
        content = results[0]["content"]
        assert "Christopher Nolan" in content
        assert "Sci-Fi" in content
        assert "8.5/10" in content

    def test_duration_minutes(self, senscritique):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = senscritique.response(MockResponse(data))
        # 8880 seconds = 148 minutes
        assert "Duration: 148 min" in results[0]["content"]
