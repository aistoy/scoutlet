"""Parser fixture tests for SoundCloud engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "soundcloud"


class MockResponse:
    def __init__(self, text, url="https://api-v2.soundcloud.com/search"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def soundcloud():
    return load_engine("soundcloud")


class TestSoundcloudParser:
    def test_filters_to_track_and_playlist(self, soundcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = soundcloud.response(MockResponse(data))
        # 3 entries: track, playlist, user (skipped)
        assert len(results) == 2

    def test_url(self, soundcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = soundcloud.response(MockResponse(data))
        assert results[0]["url"] == "https://soundcloud.com/example/track1"

    def test_iframe_src_with_uri(self, soundcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = soundcloud.response(MockResponse(data))
        # URI is URL-encoded in iframe_src
        assert "tracks%2F123" in results[0]["iframe_src"] or "tracks/123" in results[0]["iframe_src"]

    def test_published_date_isoformat(self, soundcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = soundcloud.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2024

    def test_thumbnail_artwork_url(self, soundcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = soundcloud.response(MockResponse(data))
        assert results[0]["thumbnail"] == "https://i1.sndcdn.com/artworks/abc-large.jpg"

    def test_thumbnail_falls_back_to_avatar(self, soundcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = soundcloud.response(MockResponse(data))
        # Second entry has null artwork, falls back to user.avatar_url
        assert results[1]["thumbnail"].endswith("user2.jpg")

    def test_length_timedelta(self, soundcloud):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = soundcloud.response(MockResponse(data))
        # 180000 ms = 180 seconds = 3 minutes
        assert results[0]["length"].seconds == 180
