"""Parser fixture tests for 1x (www1x) engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "www1x"


class MockResponse:
    def __init__(self, content, url="https://1x.com/backend/search.php"):
        self.content = content if isinstance(content, bytes) else content.encode("utf-8")
        self.text = self.content.decode("utf-8")
        self.url = url
        self.status_code = 200


@pytest.fixture
def www1x():
    return load_engine("www1x")


class TestWww1xParser:
    def test_returns_results(self, www1x):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = www1x.response(MockResponse(xml))
        assert len(results) == 2

    def test_url_joined_to_base(self, www1x):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = www1x.response(MockResponse(xml))
        assert results[0]["url"] == "https://1x.com/photo/123"

    def test_img_src_joined_to_gallery(self, www1x):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = www1x.response(MockResponse(xml))
        assert results[0]["img_src"].startswith("https://gallery.1x.com/")
        assert "123.jpg" in results[0]["img_src"]

    def test_title(self, www1x):
        xml = (FIXTURES_DIR / "success.xml").read_bytes()
        results = www1x.response(MockResponse(xml))
        titles = [r["title"] for r in results]
        assert "Mountain Sunset" in titles
