"""Parser fixture tests for Bitchute engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "bitchute"


class MockResponse:
    def __init__(self, text, url="https://api.bitchute.com/api/beta/search/videos"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def bitchute():
    return load_engine("bitchute")


class TestBitchuteParser:
    def test_returns_results(self, bitchute):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = bitchute.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, bitchute):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = bitchute.response(MockResponse(data))
        assert results[0]["url"] == "https://www.bitchute.com/video/abc123"

    def test_iframe_src(self, bitchute):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = bitchute.response(MockResponse(data))
        assert results[0]["iframe_src"] == "https://www.bitchute.com/embed/abc123"

    def test_published_date(self, bitchute):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = bitchute.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2024
        assert results[0]["publishedDate"].month == 3

    def test_author(self, bitchute):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = bitchute.response(MockResponse(data))
        assert results[0]["author"] == "Documentary Channel"
