"""Parser fixture tests for Mastodon (accounts) engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "mastodon"


class MockResponse:
    def __init__(self, text, url="https://mastodon.social/api/v2/search"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def mastodon():
    return load_engine("mastodon")


class TestMastodonParser:
    def test_returns_results(self, mastodon):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mastodon.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, mastodon):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mastodon.response(MockResponse(data))
        assert results[0]["url"] == "https://mastodon.social/@example"

    def test_title_includes_followers(self, mastodon):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mastodon.response(MockResponse(data))
        assert "example" in results[0]["title"]
        assert "12500 followers" in results[0]["title"]

    def test_published_date_from_created_at(self, mastodon):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mastodon.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2020

    def test_avatar_thumbnail(self, mastodon):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mastodon.response(MockResponse(data))
        assert results[0]["thumbnail"].endswith("example.png")
