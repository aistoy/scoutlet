"""Parser fixture tests for OpenClipArt engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "openclipart"


class MockResponse:
    def __init__(self, text, url="https://openclipart.org/search/"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def openclipart():
    return load_engine("openclipart")


class TestOpenClipArtParser:
    def test_returns_results(self, openclipart):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = openclipart.response(MockResponse(html))
        assert len(results) == 2

    def test_url(self, openclipart):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = openclipart.response(MockResponse(html))
        assert results[0]["url"] == "https://openclipart.org/detail/123"

    def test_img_src(self, openclipart):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = openclipart.response(MockResponse(html))
        assert results[0]["img_src"] == "https://openclipart.org/image/123.svg"

    def test_title_from_alt(self, openclipart):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = openclipart.response(MockResponse(html))
        assert results[0]["title"] == "Cat drawing"
