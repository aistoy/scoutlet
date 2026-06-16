"""Parser fixture tests for MediathekViewWeb engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "mediathekviewweb"


class MockResponse:
    def __init__(self, text, url="https://mediathekviewweb.de/api/query"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def mediathekviewweb():
    return load_engine("mediathekviewweb")


class TestMediathekViewWebParser:
    def test_returns_results(self, mediathekviewweb):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mediathekviewweb.response(MockResponse(data))
        assert len(results) == 2

    def test_url_upgraded_to_https(self, mediathekviewweb):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mediathekviewweb.response(MockResponse(data))
        assert results[0]["url"].startswith("https://")

    def test_title_includes_channel_and_duration(self, mediathekviewweb):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mediathekviewweb.response(MockResponse(data))
        assert "ARD" in results[0]["title"]
        assert "Tatort" in results[0]["title"]
        assert "1:30:00" in results[0]["title"]

    def test_length_string(self, mediathekviewweb):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mediathekviewweb.response(MockResponse(data))
        # timedelta(seconds=1800) = "0:30:00"
        assert "30:00" in results[1]["length"]
