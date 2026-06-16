"""Parser fixture tests for Dailymotion engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "dailymotion"


class MockResponse:
    def __init__(self, text, url="https://api.dailymotion.com/videos", status_code=200):
        self.text = text
        self.url = url
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def dailymotion():
    return load_engine("dailymotion")


class TestDailymotionParser:
    def test_returns_results(self, dailymotion):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = dailymotion.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, dailymotion):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = dailymotion.response(MockResponse(data))
        assert results[0]["url"] == "https://www.dailymotion.com/video/x1abcde"

    def test_thumbnail_upgraded_to_https(self, dailymotion):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = dailymotion.response(MockResponse(data))
        assert results[0]["thumbnail"].startswith("https://")

    def test_published_date_from_timestamp(self, dailymotion):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = dailymotion.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2023

    def test_iframe_only_when_embeddable(self, dailymotion):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = dailymotion.response(MockResponse(data))
        assert "iframe_src" in results[0]   # allow_embed=True
        assert "iframe_src" not in results[1]  # allow_embed=False

    def test_length_minutes_seconds(self, dailymotion):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = dailymotion.response(MockResponse(data))
        # 600s = 10:00
        assert results[0]["length"] == "10:00"
        # 3661s = 01:01:01 (strftime %H zero-pads)
        assert results[1]["length"] == "01:01:01"
