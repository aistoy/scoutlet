"""Parser fixture tests for Flickr (api_key) engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "flickr"


class MockResponse:
    def __init__(self, text, url="https://api.flickr.com/services/rest/"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def flickr():
    return load_engine("flickr", api_key="test-key")


class TestFlickrParser:
    def test_skips_photos_without_url(self, flickr):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = flickr.response(MockResponse(data))
        # 3 photos, 1 skipped (no url_o/url_z)
        assert len(results) == 2

    def test_url_built_from_owner_id(self, flickr):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = flickr.response(MockResponse(data))
        assert results[0]["url"] == "https://www.flickr.com/photos/12345678@N00/11111111111"

    def test_prefers_url_o_over_z(self, flickr):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = flickr.response(MockResponse(data))
        assert results[0]["img_src"].endswith("_o.jpg")
        # Second has only url_z
        assert results[1]["img_src"].endswith("_z.jpg")

    def test_thumbnail_uses_url_n(self, flickr):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = flickr.response(MockResponse(data))
        assert results[0]["thumbnail_src"].endswith("_n.jpg")

    def test_request_includes_api_key(self, flickr):
        params = {"pageno": 1}
        flickr.request("test", params)
        assert "api_key=test-key" in params["url"]
