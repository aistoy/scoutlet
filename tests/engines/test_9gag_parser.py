"""Parser fixture tests for 9GAG engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "9gag"


class MockResponse:
    def __init__(self, text, url="https://9gag.com/v1/search-posts"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def gag():
    return load_engine("9gag")


class Test9GagParser:
    def test_returns_results_and_suggestions(self, gag):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = gag.response(MockResponse(data))
        # 2 posts + 2 suggestions
        assert len(results) == 4

    def test_photo_uses_images_template(self, gag):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = gag.response(MockResponse(data))
        photo = [r for r in results if r.get("template") == "images.html"]
        assert len(photo) == 1

    def test_animated_uses_videos_template(self, gag):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = gag.response(MockResponse(data))
        animated = [r for r in results if r.get("template") == "videos.html"]
        assert len(animated) == 1

    def test_thumbnail_uses_fb_when_tall(self, gag):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = gag.response(MockResponse(data))
        # First photo: image700.height=500 (>400) -> uses imageFbThumbnail
        photo_results = [r for r in results if r.get("template") == "images.html"]
        assert "catFb" in photo_results[0]["thumbnail_src"]

    def test_thumbnail_uses_image700_when_short(self, gag):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = gag.response(MockResponse(data))
        # Second animated: image700.height=300 (<400) -> uses image700
        animated_results = [r for r in results if r.get("template") == "videos.html"]
        assert "dog700" in animated_results[0]["thumbnail"]

    def test_suggestions_appended(self, gag):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = gag.response(MockResponse(data))
        suggestions = [r for r in results if "suggestion" in r]
        assert len(suggestions) == 2
