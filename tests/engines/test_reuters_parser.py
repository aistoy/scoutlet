"""Parser fixture tests for Reuters engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "reuters"


class MockResponse:
    def __init__(self, text, url="https://www.reuters.com/pf/api/v3/content/fetch/articles-by-search-v2"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def reuters():
    return load_engine("reuters")


class TestReutersParser:
    def test_returns_results(self, reuters):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = reuters.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, reuters):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = reuters.response(MockResponse(data))
        assert results[0]["url"].startswith("https://www.reuters.com/article/abc123")
        assert results[0]["url"].endswith("some-news/")

    def test_published_date_isoformat(self, reuters):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = reuters.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2024

    def test_thumbnail_resizer_url_with_height(self, reuters):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = reuters.response(MockResponse(data))
        assert "height=80" in results[0]["thumbnail"]

    def test_empty_thumbnail_when_no_resizer(self, reuters):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = reuters.response(MockResponse(data))
        # Second article has empty thumbnail
        assert results[1]["thumbnail"] == ""

    def test_metadata_from_kicker(self, reuters):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = reuters.response(MockResponse(data))
        assert results[0]["metadata"] == "World"
