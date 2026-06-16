"""Parser fixture tests for Bing Images engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "bing_images"


class MockResponse:
    def __init__(self, text: str, url: str = "https://www.bing.com/images/search?q=test"):
        self.text = text
        self.url = url
        self.status_code = 200
        self.search_params = {}


@pytest.fixture
def bing_images():
    return load_engine("bing_images")


class TestBingImagesParser:
    def test_success_returns_results(self, bing_images):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing_images.response(resp)
        assert len(results) >= 1

    def test_result_has_url(self, bing_images):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing_images.response(resp)
        for r in results:
            assert r["url"], "Result missing url"
            assert r["url"].startswith("http"), f"Invalid URL: {r['url']}"

    def test_result_has_title(self, bing_images):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing_images.response(resp)
        for r in results:
            assert r["title"], "Result missing title"

    def test_result_has_img_src(self, bing_images):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing_images.response(resp)
        assert any(r.get("img_src") for r in results), "No result has img_src"

    def test_result_has_thumbnail(self, bing_images):
        html = (FIXTURES_DIR / "success_minimal.html").read_text()
        resp = MockResponse(html)
        results = bing_images.response(resp)
        assert any(r.get("thumbnail_src") or r.get("thumbnail") for r in results), "No result has thumbnail"
