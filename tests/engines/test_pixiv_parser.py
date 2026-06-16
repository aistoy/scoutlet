"""Parser fixture tests for Pixiv engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "pixiv"


class MockResponse:
    def __init__(self, text, url="https://www.pixiv.net/ajax/search/illustrations"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def pixiv():
    return load_engine("pixiv")


class TestPixivParser:
    def test_returns_results(self, pixiv):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pixiv.response(MockResponse(data))
        assert len(results) == 2

    def test_url_without_proxy_is_unchanged(self, pixiv):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pixiv.response(MockResponse(data))
        # No proxies configured - URL stays as i.pximg.net
        assert "i.pximg.net" in results[0]["url"]

    def test_author_includes_user_id(self, pixiv):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pixiv.response(MockResponse(data))
        assert "artist1" in results[0]["author"]
        assert "111" in results[0]["author"]

    def test_title_from_item(self, pixiv):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pixiv.response(MockResponse(data))
        titles = [r["title"] for r in results]
        assert "Original Character" in titles
        assert "Landscape" in titles
