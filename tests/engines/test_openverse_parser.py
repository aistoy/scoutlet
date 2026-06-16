"""Parser fixture tests for Openverse engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "openverse"


class MockResponse:
    def __init__(self, text, url="https://api.openverse.org/v1/images/"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def openverse():
    return load_engine("openverse")


class TestOpenverseParser:
    def test_returns_results(self, openverse):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openverse.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, openverse):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openverse.response(MockResponse(data))
        assert results[0]["url"] == "https://example.com/photo/1"

    def test_img_src(self, openverse):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openverse.response(MockResponse(data))
        assert results[0]["img_src"] == "https://cdn.example.com/images/1.jpg"

    def test_title(self, openverse):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = openverse.response(MockResponse(data))
        assert results[0]["title"] == "Mountain Sunset"
