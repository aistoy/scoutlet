"""Parser fixture tests for Moviepilot engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "moviepilot"


class MockResponse:
    def __init__(self, text, url="https://www.moviepilot.de/api/search", status_code=200):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.search_params = {}

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def moviepilot():
    return load_engine("moviepilot")


class TestMoviepilotParser:
    def test_returns_search_results(self, moviepilot):
        data = (FIXTURES_DIR / "success_search.json").read_text()
        resp = MockResponse(data, url="https://www.moviepilot.de/api/search")
        results = moviepilot.response(resp)
        assert len(results) == 2
        assert results[0]["title"] == "Inception"

    def test_search_url_in_result(self, moviepilot):
        data = (FIXTURES_DIR / "success_search.json").read_text()
        resp = MockResponse(data, url="https://www.moviepilot.de/api/search")
        results = moviepilot.response(resp)
        assert results[0]["url"] == "https://www.moviepilot.de/movies/inception"

    def test_discovery_uses_path(self, moviepilot):
        data = (FIXTURES_DIR / "success_discovery.json").read_text()
        resp = MockResponse(data, url="https://www.moviepilot.de/api/discovery")
        results = moviepilot.response(resp)
        assert results[0]["url"] == "https://www.moviepilot.de/movies/the-matrix"

    def test_discovery_thumbnail_built(self, moviepilot):
        data = (FIXTURES_DIR / "success_discovery.json").read_text()
        resp = MockResponse(data, url="https://www.moviepilot.de/api/discovery")
        results = moviepilot.response(resp)
        assert "matrix-img" in results[0]["thumbnail"]
        assert "matrix.jpg" in results[0]["thumbnail"]

    def test_request_search_no_filter(self, moviepilot):
        params = {"pageno": 1}
        moviepilot.request("Inception", params)
        assert "/api/search" in params["url"]
        assert params["moviepilot_discovery"] is False

    def test_request_discovery_with_filter(self, moviepilot):
        params = {"pageno": 1}
        moviepilot.request("genre-actionfilm", params)
        assert "/api/discovery" in params["url"]
        assert params["moviepilot_discovery"] is True
