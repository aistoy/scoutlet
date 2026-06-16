"""Parser fixture tests for FindThatMeme engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "findthatmeme"


class MockResponse:
    def __init__(self, text, url="https://findthatmeme.com/api/v1/search"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def findthatmeme():
    return load_engine("findthatmeme")


class TestFindThatMemeParser:
    def test_returns_results(self, findthatmeme):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = findthatmeme.response(MockResponse(data))
        assert len(results) == 2

    def test_image_url_for_image_type(self, findthatmeme):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = findthatmeme.response(MockResponse(data))
        assert "/memes/2024/01/abc123.png" in results[0]["img_src"]

    def test_thumb_url_for_gif_type(self, findthatmeme):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = findthatmeme.response(MockResponse(data))
        # GIF uses thumb (not image_path directly)
        assert "/thumb/" in results[1]["img_src"]

    def test_published_date_parsed_iso(self, findthatmeme):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = findthatmeme.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2024
        assert results[0]["publishedDate"].month == 1

    def test_filesize_humanized(self, findthatmeme):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = findthatmeme.response(MockResponse(data))
        assert "KB" in results[0]["filesize"]
        assert "MB" in results[1]["filesize"]
