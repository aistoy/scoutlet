"""Parser fixture tests for SepiaSearch engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "sepiasearch"


class MockResponse:
    def __init__(self, text, url="https://sepiasearch.org/api/v1/search/videos"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def sepiasearch():
    return load_engine("sepiasearch")


class TestSepiasearchParser:
    def test_returns_results(self, sepiasearch):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = sepiasearch.response(MockResponse(data))
        assert len(results) == 1

    def test_url(self, sepiasearch):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = sepiasearch.response(MockResponse(data))
        assert results[0]["url"] == "https://sepiasearch.org/videos/watch/xyz789"

    def test_published_date(self, sepiasearch):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = sepiasearch.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2024

    def test_metadata_includes_channel(self, sepiasearch):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = sepiasearch.response(MockResponse(data))
        assert "Fediverse Channel" in results[0]["metadata"]
