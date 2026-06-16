"""Parser fixture tests for Pexels engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "pexels"


class MockResponse:
    def __init__(self, text, url="https://www.pexels.com/api/v3/search/photos"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def pexels():
    return load_engine("pexels")


class TestPexelsParser:
    def test_returns_results(self, pexels):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pexels.response(MockResponse(data))
        assert len(results) == 2

    def test_url_with_slug_and_id(self, pexels):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pexels.response(MockResponse(data))
        assert results[0]["url"] == "https://www.pexels.com/photo/mountain-sunrise-12345/"

    def test_img_src_uses_download_link(self, pexels):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pexels.response(MockResponse(data))
        assert results[0]["img_src"].endswith("original.jpg")

    def test_resolution_field(self, pexels):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pexels.response(MockResponse(data))
        assert results[0]["resolution"] == "4000x2667"

    def test_request_includes_api_key_header(self, pexels):
        params = {"pageno": 1, "headers": {}}
        pexels.request("test", params)
        assert "secret-key" in params["headers"]
