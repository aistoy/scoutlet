"""Parser fixture tests for Peertube engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "peertube"


class MockResponse:
    def __init__(self, text, url="https://peer.tube/api/v1/search/videos"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def peertube():
    return load_engine("peertube")


class TestPeertubeParser:
    def test_returns_results(self, peertube):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = peertube.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, peertube):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = peertube.response(MockResponse(data))
        assert results[0]["url"] == "https://peer.tube/videos/watch/abc123"

    def test_length_timedelta(self, peertube):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = peertube.response(MockResponse(data))
        assert results[0]["length"].total_seconds() == 1800

    def test_published_date_isoformat(self, peertube):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = peertube.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2024

    def test_metadata_includes_channel_and_tags(self, peertube):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = peertube.response(MockResponse(data))
        assert "FSF Channel" in results[0]["metadata"]
        assert "fsf@peer.tube" in results[0]["metadata"]
        assert "opensource" in results[0]["metadata"]
