"""Parser fixture tests for Artic engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "artic"


class MockResponse:
    def __init__(self, text, url="https://api.artic.edu/api/v1/artworks/search"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def artic():
    return load_engine("artic")


class TestArticParser:
    def test_skips_no_image_id(self, artic):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = artic.response(MockResponse(data))
        # 3 entries, 1 skipped (no image_id)
        assert len(results) == 2

    def test_url_built(self, artic):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = artic.response(MockResponse(data))
        assert results[0]["url"] == "https://artic.edu/artworks/111628"

    def test_img_src(self, artic):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = artic.response(MockResponse(data))
        assert "abcd1234" in results[0]["img_src"]
        assert results[0]["img_src"].endswith("/default.jpg")

    def test_title_includes_date_and_artist(self, artic):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = artic.response(MockResponse(data))
        assert "American Gothic" in results[0]["title"]
        assert "1930" in results[0]["title"]
