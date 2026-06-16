"""Parser fixture tests for Frinkiac engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "frinkiac"


class MockResponse:
    def __init__(self, text, url="https://frinkiac.com/api/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def frinkiac():
    return load_engine("frinkiac")


class TestFrinkiacParser:
    def test_returns_results(self, frinkiac):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = frinkiac.response(MockResponse(data))
        assert len(results) == 3

    def test_url_with_caption_episode_timestamp(self, frinkiac):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = frinkiac.response(MockResponse(data))
        url = results[0]["url"]
        assert "p=caption" in url
        assert "e=S05E06" in url
        assert "t=560727" in url

    def test_thumbnail_uses_medium_jpg(self, frinkiac):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = frinkiac.response(MockResponse(data))
        assert results[0]["thumbnail_src"].endswith("/S05E06/560727/medium.jpg")

    def test_img_src_full_resolution(self, frinkiac):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = frinkiac.response(MockResponse(data))
        assert results[0]["img_src"].endswith("/S05E06/560727.jpg")

    def test_title_from_record(self, frinkiac):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = frinkiac.response(MockResponse(data))
        assert results[0]["title"] == "Marge on the Lam"
        assert "Hello? Hellodilly-odilly?" in results[0]["content"]

    def test_request_uses_api_search_endpoint(self, frinkiac):
        params = {"pageno": 1}
        frinkiac.request("hello", params)
        assert "/api/search" in params["url"]
        assert "q=hello" in params["url"]
