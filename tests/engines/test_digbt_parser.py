"""Parser fixture tests for Digbt engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "digbt"


class MockResponse:
    def __init__(self, text, url="https://digbt.org/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def digbt():
    return load_engine("digbt")


class TestDigbtParser:
    def test_returns_results(self, digbt):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = digbt.response(MockResponse(html))
        assert len(results) == 2

    def test_url(self, digbt):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = digbt.response(MockResponse(html))
        assert results[0]["url"] == "https://digbt.org/download/ubuntu-22.04"

    def test_magnetlink(self, digbt):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = digbt.response(MockResponse(html))
        assert results[0]["magnetlink"].startswith("magnet:?xt=urn:btih:")

    def test_filesize(self, digbt):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = digbt.response(MockResponse(html))
        # The original SearXNG format expects files_data[3] = size, [4] = unit
        # e.g. tail text "100 Seeders 5 Leechers 4.5 GB magnet"
        assert results[0]["filesize"]

    def test_torrent_template(self, digbt):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = digbt.response(MockResponse(html))
        assert results[0]["template"] == "torrent.html"
