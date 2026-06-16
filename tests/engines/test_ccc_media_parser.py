"""Parser fixture tests for media.ccc.de engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "ccc_media"


class MockResponse:
    def __init__(self, text, url="https://api.media.ccc.de/public/events/search"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def ccc_media():
    return load_engine("ccc_media")


class TestCCCMediaParser:
    def test_returns_results(self, ccc_media):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ccc_media.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, ccc_media):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ccc_media.response(MockResponse(data))
        assert results[0]["url"] == "https://media.ccc.de/v/example-1"

    def test_prefers_mp4_over_webm(self, ccc_media):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ccc_media.response(MockResponse(data))
        # First event has both webm and mp4; mp4 wins
        assert results[0]["iframe_src"].endswith(".mp4")

    def test_published_date_isoformat(self, ccc_media):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ccc_media.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2023

    def test_missing_published_date(self, ccc_media):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ccc_media.response(MockResponse(data))
        assert results[1]["publishedDate"] is None

    def test_length_timedelta(self, ccc_media):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ccc_media.response(MockResponse(data))
        assert results[0]["length"].total_seconds() == 3300
