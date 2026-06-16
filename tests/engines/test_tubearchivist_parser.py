"""Parser fixture tests for Tube Archivist engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "tubearchivist"


class MockResponse:
    def __init__(self, text, url="https://example.com/api/search/"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def tubearchivist():
    return load_engine("tubearchivist", base_url="https://ta.example.com", ta_token="test-token")


class TestTubeArchivistParser:
    def test_returns_results(self, tubearchivist):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = tubearchivist.response(MockResponse(data))
        # 1 channel + 2 videos = 3 results
        assert len(results) == 3

    def test_channel_url(self, tubearchivist):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = tubearchivist.response(MockResponse(data))
        assert results[0]["url"] == "https://ta.example.com/channel/chan1"

    def test_video_url_default(self, tubearchivist):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = tubearchivist.response(MockResponse(data))
        # Default: link to TA interface (not mp4)
        assert "/?videoId=vid1" in results[1]["url"]

    def test_published_date_isoformat(self, tubearchivist):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = tubearchivist.response(MockResponse(data))
        assert results[1]["publishedDate"].year == 2024

    def test_thumbnail_includes_auth_token(self, tubearchivist):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = tubearchivist.response(MockResponse(data))
        assert "auth=test-token" in results[1]["thumbnail"]

    def test_setup_rejects_missing_config(self):
        e = load_engine("tubearchivist")
        assert e is None
