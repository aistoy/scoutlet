"""Parser fixture tests for Deviantart engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "deviantart"


class MockResponse:
    def __init__(self, text, url="https://www.deviantart.com/search?q=test"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def deviantart():
    return load_engine("deviantart")


class TestDeviantartParser:
    def test_skips_premium_content(self, deviantart):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = deviantart.response(MockResponse(html))
        # 3 entries in fixture, 1 is premium (skipped)
        assert len(results) == 2

    def test_url(self, deviantart):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = deviantart.response(MockResponse(html))
        assert results[0]["url"] == "https://www.deviantart.com/artwork1"

    def test_img_src_strips_v1_path(self, deviantart):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = deviantart.response(MockResponse(html))
        assert "/v1" not in results[0]["img_src"]

    def test_title_from_aria_label(self, deviantart):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = deviantart.response(MockResponse(html))
        titles = [r["title"] for r in results]
        assert "Sunset Painting" in titles
        assert "Portrait Study" in titles
