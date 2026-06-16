"""Parser fixture tests for Artstation engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "artstation"


class MockResponse:
    def __init__(self, text, url="https://www.artstation.com/api/v2/search/projects.json"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def artstation():
    return load_engine("artstation")


class TestArtstationParser:
    def test_returns_results(self, artstation):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = artstation.response(MockResponse(data))
        assert len(results) == 2

    def test_full_image_url_rewrites_thumb(self, artstation):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = artstation.response(MockResponse(data))
        assert "/large/" in results[0]["img_src"]
        assert "smaller_square" not in results[0]["img_src"]

    def test_thumbnail_uses_smaller_square(self, artstation):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = artstation.response(MockResponse(data))
        assert "smaller_square" in results[0]["thumbnail_src"]

    def test_author_includes_username_and_full_name(self, artstation):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = artstation.response(MockResponse(data))
        assert "artist1" in results[0]["author"]
        assert "Artist One" in results[0]["author"]
