"""Parser fixture tests for Pinterest engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "pinterest"


class MockResponse:
    def __init__(self, text, url="https://www.pinterest.com/resource/"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def pinterest():
    return load_engine("pinterest")


class TestPinterestParser:
    def test_skips_stories(self, pinterest):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pinterest.response(MockResponse(data))
        # 3 entries, 1 story (skipped)
        assert len(results) == 2

    def test_url_from_link_field(self, pinterest):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pinterest.response(MockResponse(data))
        assert results[0]["url"] == "https://example.com/pin1"

    def test_url_fallback_to_pin_id(self, pinterest):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pinterest.response(MockResponse(data))
        # Second result has no link
        assert results[1]["url"] == "https://www.pinterest.com/pin/333/"

    def test_resolution_from_orig(self, pinterest):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pinterest.response(MockResponse(data))
        assert results[0]["resolution"] == "1000x800"

    def test_author_includes_pinner(self, pinterest):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pinterest.response(MockResponse(data))
        assert "Jane D" in results[0]["author"]
        assert "janed" in results[0]["author"]
