"""Parser fixture tests for Sogou Videos engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "sogou_videos"


class MockResponse:
    def __init__(self, text, url="https://v.sogou.com/api/video/shortVideoV2"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def sogou_videos():
    return load_engine("sogou_videos")


class TestSogouVideosParser:
    def test_returns_results(self, sogou_videos):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = sogou_videos.response(MockResponse(data))
        # 3 entries, 1 skipped (no url)
        assert len(results) == 2

    def test_relative_url_resolved(self, sogou_videos):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = sogou_videos.response(MockResponse(data))
        assert results[0]["url"] == "https://v.sogou.com/vc/np/abc123"

    def test_absolute_url_unchanged(self, sogou_videos):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = sogou_videos.response(MockResponse(data))
        assert results[1]["url"] == "https://example.com/v/def456"

    def test_published_date(self, sogou_videos):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = sogou_videos.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2024

    def test_length_timedelta(self, sogou_videos):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = sogou_videos.response(MockResponse(data))
        # 3:45 = 225 seconds
        assert results[0]["length"].seconds == 225
