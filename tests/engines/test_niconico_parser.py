"""Parser fixture tests for Niconico engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "niconico"


class MockResponse:
    def __init__(self, text, url="https://www.nicovideo.jp/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def niconico():
    return load_engine("niconico")


class TestNiconicoParser:
    def test_returns_results(self, niconico):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = niconico.response(MockResponse(html))
        assert len(results) == 2

    def test_url_built_from_video_id(self, niconico):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = niconico.response(MockResponse(html))
        assert results[0]["url"] == "https://www.nicovideo.jp/watch/sm12345"

    def test_iframe_src(self, niconico):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = niconico.response(MockResponse(html))
        assert results[0]["iframe_src"] == "https://embed.nicovideo.jp/watch/sm12345"

    def test_length_timedelta(self, niconico):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = niconico.response(MockResponse(html))
        # 04:30 = 4 min 30 sec = 270 seconds
        assert results[0]["length"].seconds == 270

    def test_published_date(self, niconico):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = niconico.response(MockResponse(html))
        assert results[0]["publishedDate"].year == 2024
        assert results[0]["publishedDate"].month == 1
