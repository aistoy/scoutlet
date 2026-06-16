"""Parser fixture tests for Emojipedia engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "emojipedia"


class MockResponse:
    def __init__(self, text, url="https://emojipedia.org/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def emojipedia():
    return load_engine("emojipedia")


class TestEmojipediaParser:
    def test_returns_only_emoji_list_links(self, emojipedia):
        html_text = (FIXTURES_DIR / "success.html").read_text()
        results = emojipedia.response(MockResponse(html_text))
        # 3 emoji links + 1 sidebar link (sidebar is outside EmojisList div)
        assert len(results) == 3

    def test_url(self, emojipedia):
        html_text = (FIXTURES_DIR / "success.html").read_text()
        results = emojipedia.response(MockResponse(html_text))
        assert results[0]["url"] == "https://emojipedia.org/red-heart"

    def test_title_includes_emoji_glyph_and_name(self, emojipedia):
        html_text = (FIXTURES_DIR / "success.html").read_text()
        results = emojipedia.response(MockResponse(html_text))
        assert "Red Heart" in results[0]["title"]
        assert "❤" in results[0]["title"]

    def test_request_uses_search_endpoint(self, emojipedia):
        params = {"pageno": 1}
        emojipedia.request("heart", params)
        assert "/search" in params["url"]
        assert "q=heart" in params["url"]
