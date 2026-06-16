"""Parser fixture tests for YouTube Data API engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine
from scoutlet.exceptions import SearchEngineAPIException

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "youtube_api"


class MockResponse:
    def __init__(self, text, url="https://www.googleapis.com/youtube/v3/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def youtube_api():
    return load_engine("youtube_api", api_key="test-key")


class TestYouTubeAPIParser:
    def test_skips_non_video(self, youtube_api):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = youtube_api.response(MockResponse(data))
        # 3 items: 2 videos + 1 channel (skipped)
        assert len(results) == 2

    def test_url(self, youtube_api):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = youtube_api.response(MockResponse(data))
        assert results[0]["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_iframe_src(self, youtube_api):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = youtube_api.response(MockResponse(data))
        assert "/embed/dQw4w9WgXcQ" in results[0]["iframe_src"]

    def test_published_date_isoformat(self, youtube_api):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = youtube_api.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2009

    def test_error_raises_api_exception(self, youtube_api):
        data = (FIXTURES_DIR / "error.json").read_text()
        with pytest.raises(SearchEngineAPIException):
            youtube_api.response(MockResponse(data))

    def test_setup_rejects_missing_key(self):
        e = load_engine("youtube_api")
        assert e is None
