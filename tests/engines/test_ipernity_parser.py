"""Parser fixture tests for Ipernity engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "ipernity"


class MockResponse:
    def __init__(self, text, url="https://www.ipernity.com/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def ipernity():
    return load_engine("ipernity")


class TestIpernityParser:
    def test_returns_results(self, ipernity):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ipernity.response(MockResponse(html))
        assert len(results) == 2

    def test_url_built_from_user_doc_id(self, ipernity):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ipernity.response(MockResponse(html))
        assert results[0]["url"] == "https://www.ipernity.com/doc/12345/67890"

    def test_img_src_uses_640(self, ipernity):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ipernity.response(MockResponse(html))
        assert "640.jpg" in results[0]["img_src"]
        assert "240.jpg" in results[0]["thumbnail_src"]

    def test_resolution(self, ipernity):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ipernity.response(MockResponse(html))
        assert results[0]["resolution"] == "1024x768"

    def test_published_date_from_timestamp(self, ipernity):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = ipernity.response(MockResponse(html))
        assert results[0]["publishedDate"] is not None
        assert results[0]["publishedDate"].year >= 2023
