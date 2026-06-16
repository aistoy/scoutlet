"""Parser fixture tests for Flickr (no api_key) engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "flickr_noapi"


class MockResponse:
    def __init__(self, text, url="https://www.flickr.com/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def flickr_noapi():
    return load_engine("flickr_noapi")


class TestFlickrNoAPIParser:
    def test_parses_model_export(self, flickr_noapi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = flickr_noapi.response(MockResponse(html))
        assert len(results) == 1

    def test_extracts_url_from_owner_nsid(self, flickr_noapi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = flickr_noapi.response(MockResponse(html))
        assert results[0]["url"] == "https://www.flickr.com/photos/123@N00/111"

    def test_img_src_picks_largest_size(self, flickr_noapi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = flickr_noapi.response(MockResponse(html))
        assert results[0]["img_src"].endswith("_o.jpg")

    def test_thumbnail_uses_n_size(self, flickr_noapi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = flickr_noapi.response(MockResponse(html))
        assert results[0]["thumbnail_src"].endswith("_n.jpg")

    def test_empty_html_returns_empty(self, flickr_noapi):
        results = flickr_noapi.response(MockResponse("<html></html>"))
        assert results == []
