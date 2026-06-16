"""Parser fixture tests for Sogou Images engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "sogou_images"


class MockResponse:
    def __init__(self, text, url="https://pic.sogou.com/pics"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def sogou_images():
    return load_engine("sogou_images")


class TestSogouImagesParser:
    def test_returns_results(self, sogou_images):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = sogou_images.response(MockResponse(html))
        assert len(results) == 2

    def test_url(self, sogou_images):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = sogou_images.response(MockResponse(html))
        assert results[0]["url"] == "https://example.com/page1"

    def test_img_src(self, sogou_images):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = sogou_images.response(MockResponse(html))
        assert results[0]["img_src"] == "https://pic.example.com/1.jpg"

    def test_title(self, sogou_images):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = sogou_images.response(MockResponse(html))
        titles = [r["title"] for r in results]
        assert "Cat photo" in titles

    def test_empty_html(self, sogou_images):
        results = sogou_images.response(MockResponse("<html></html>"))
        assert results == []
