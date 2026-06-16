"""Parser fixture tests for YouTube (no api_key) engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "youtube_noapi"


class MockResponse:
    def __init__(self, text, url="https://www.youtube.com/results"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def youtube_noapi():
    return load_engine("youtube_noapi")


class TestYouTubeNoAPIParser:
    def test_returns_results(self, youtube_noapi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = youtube_noapi.response(MockResponse(html))
        # 2 videoRenderer items + 1 channelRenderer (skipped)
        assert len(results) == 2

    def test_url(self, youtube_noapi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = youtube_noapi.response(MockResponse(html))
        assert results[0]["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_thumbnail(self, youtube_noapi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = youtube_noapi.response(MockResponse(html))
        assert "i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg" in results[0]["thumbnail"]

    def test_iframe_src(self, youtube_noapi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = youtube_noapi.response(MockResponse(html))
        assert "/embed/dQw4w9WgXcQ" in results[0]["iframe_src"]

    def test_length(self, youtube_noapi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = youtube_noapi.response(MockResponse(html))
        assert results[0]["length"] == "3:33"
