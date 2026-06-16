"""Parser fixture tests for Mixcloud engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "mixcloud"


class MockResponse:
    def __init__(self, text, url="https://api.mixcloud.com/search/"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def mixcloud():
    return load_engine("mixcloud")


class TestMixcloudParser:
    def test_returns_results(self, mixcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mixcloud.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, mixcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mixcloud.response(MockResponse(data))
        assert results[0]["url"] == "https://www.mixcloud.com/exampledj/example-mix/"

    def test_iframe_src(self, mixcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mixcloud.response(MockResponse(data))
        assert "feed=" in results[0]["iframe_src"]
        assert "example-mix" in results[0]["iframe_src"]

    def test_published_date_isoformat(self, mixcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mixcloud.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2024

    def test_thumbnail_medium(self, mixcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mixcloud.response(MockResponse(data))
        assert results[0]["thumbnail"].endswith("mix-medium.jpg")
