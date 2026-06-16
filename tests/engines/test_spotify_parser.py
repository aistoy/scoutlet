"""Parser fixture tests for Spotify engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "spotify"


class MockResponse:
    def __init__(self, text, url="https://api.spotify.com/v1/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def spotify():
    return load_engine("spotify", api_client_id="test-id", api_client_secret="test-secret")


class TestSpotifyParser:
    def test_returns_results(self, spotify):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = spotify.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, spotify):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = spotify.response(MockResponse(data))
        assert results[0]["url"] == "https://open.spotify.com/track/track1abc"

    def test_iframe_src_with_track_id(self, spotify):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = spotify.response(MockResponse(data))
        assert "track1abc" in results[0]["iframe_src"]

    def test_content_format(self, spotify):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = spotify.response(MockResponse(data))
        assert "Famous Artist" in results[0]["content"]
        assert "Greatest Hits" in results[0]["content"]
        assert "Hit Song" in results[0]["content"]

    def test_setup_rejects_missing_credentials(self):
        e = load_engine("spotify")
        assert e is None
