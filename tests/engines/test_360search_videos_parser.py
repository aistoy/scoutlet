"""Parser fixture tests for 360Search Videos engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "360search_videos"


class MockResponse:
    def __init__(self, text, url="https://tv.360kan.com/v1/video/list"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def engine():
    return load_engine("360search_videos")


class Test360SearchVideosParser:
    def test_returns_results(self, engine):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = engine.response(MockResponse(data))
        # 3 entries, 1 skipped (no play_url)
        assert len(results) == 2

    def test_url(self, engine):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = engine.response(MockResponse(data))
        assert results[0]["url"] == "https://www.youtube.com/watch?v=abc123"

    def test_published_date_from_timestamp(self, engine):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = engine.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2023

    def test_thumbnail(self, engine):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = engine.response(MockResponse(data))
        assert results[0]["thumbnail"] == "https://example.com/thumb1.jpg"
