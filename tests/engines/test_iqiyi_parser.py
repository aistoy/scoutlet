"""Parser fixture tests for iQiyi engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "iqiyi"


class MockResponse:
    def __init__(self, text, url="https://mesh.if.iqiyi.com/portal/lw/search/homePageV3"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def iqiyi():
    return load_engine("iqiyi")


class TestIqiyiParser:
    def test_returns_results(self, iqiyi):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = iqiyi.response(MockResponse(data))
        # 1 album with 2 videos + 1 album single = 3 results
        assert len(results) == 3

    def test_url_upgrades_to_https(self, iqiyi):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = iqiyi.response(MockResponse(data))
        # First video has http:// pageUrl
        assert results[0]["url"].startswith("https://")

    def test_published_date(self, iqiyi):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = iqiyi.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2024
        assert results[0]["publishedDate"].month == 1

    def test_length_timedelta(self, iqiyi):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = iqiyi.response(MockResponse(data))
        # 2700000 ms = 2700 seconds = 45 minutes
        assert results[0]["length"].total_seconds() == 2700

    def test_thumbnail(self, iqiyi):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = iqiyi.response(MockResponse(data))
        assert results[0]["thumbnail"] == "https://example.com/drama.jpg"
