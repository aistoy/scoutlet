"""Parser fixture tests for Pixabay engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "pixabay"


class MockResponse:
    def __init__(self, text, url="https://pixabay.com/images/search/", status_code=200):
        self.text = text
        self.url = url
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def pixabay():
    return load_engine("pixabay")


class TestPixabayParser:
    def test_handles_photo_and_video(self, pixabay):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pixabay.response(MockResponse(data))
        assert len(results) == 2
        assert results[0]["template"] == "images.html"
        assert results[1]["template"] == "videos.html"

    def test_image_picks_first_smallest_last_largest(self, pixabay):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pixabay.response(MockResponse(data))
        assert "/small/" in results[0]["thumbnail_src"]
        assert "/large/" in results[0]["img_src"]

    def test_video_thumbnail_and_iframe(self, pixabay):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pixabay.response(MockResponse(data))
        assert "/thumb/" in results[1]["thumbnail"]
        assert "/embed/" in results[1]["iframe_src"]

    def test_video_published_date(self, pixabay):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pixabay.response(MockResponse(data))
        assert results[1]["publishedDate"].year == 2024

    def test_redirect_returns_empty(self, pixabay):
        data = (FIXTURES_DIR / "success.json").read_text()
        # 302 status means "no results on this page"
        results = pixabay.response(MockResponse(data, status_code=302))
        assert results == []
