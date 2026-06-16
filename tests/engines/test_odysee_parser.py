"""Parser fixture tests for Odysee engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "odysee"


class MockResponse:
    def __init__(self, text, url="https://lighthouse.odysee.tv/search"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def odysee():
    return load_engine("odysee")


class TestOdyseeParser:
    def test_returns_results(self, odysee):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = odysee.response(MockResponse(data))
        assert len(results) == 2

    def test_url_built_from_name_and_claim(self, odysee):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = odysee.response(MockResponse(data))
        assert results[0]["url"] == "https://odysee.com/v1:abc123"

    def test_iframe_src_uses_embed(self, odysee):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = odysee.response(MockResponse(data))
        assert "/$/embed/" in results[0]["iframe_src"]

    def test_published_date(self, odysee):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = odysee.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2024

    def test_length_minutes_format(self, odysee):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = odysee.response(MockResponse(data))
        # 1800s = 30:00, 3661s = 01:01:01 (strftime %H zero-pads)
        assert results[0]["length"] == "30:00"
        assert results[1]["length"] == "01:01:01"

    def test_thumbnail_via_odycdn(self, odysee):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = odysee.response(MockResponse(data))
        assert "thumbnails.odycdn.com" in results[0]["thumbnail"]
