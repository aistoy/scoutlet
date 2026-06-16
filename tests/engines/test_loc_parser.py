"""Parser fixture tests for Library of Congress engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "loc"


class MockResponse:
    def __init__(self, text, url="https://www.loc.gov/photos/", status_code=200):
        self.text = text
        self.url = url
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def loc():
    return load_engine("loc")


class TestLocParser:
    def test_skips_no_image(self, loc):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = loc.response(MockResponse(data))
        # 2 entries, 1 has no image
        assert len(results) == 1

    def test_url_from_link(self, loc):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = loc.response(MockResponse(data))
        assert results[0]["url"] == "https://www.loc.gov/pictures/collection/2023/item/123/"

    def test_title_brackets_stripped(self, loc):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = loc.response(MockResponse(data))
        assert results[0]["title"] == "Migrant Mother"

    def test_img_src_uses_last_url(self, loc):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = loc.response(MockResponse(data))
        assert results[0]["img_src"] == "https://cdn.loc.gov/full/123.jpg"

    def test_thumbnail_uses_first_url(self, loc):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = loc.response(MockResponse(data))
        assert results[0]["thumbnail_src"] == "https://cdn.loc.gov/thumb/123.jpg"
