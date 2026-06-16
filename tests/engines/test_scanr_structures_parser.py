"""Parser fixture tests for scanr_structures engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "scanr_structures"


class MockResponse:
    def __init__(self, text: str, url: str = "https://scanr.enseignementsup-recherche.gouv.fr/api/structures/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def scanr():
    return load_engine("scanr_structures")


class TestScanRStructuresParser:
    def test_returns_results(self, scanr):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = scanr.response(MockResponse(data))
        assert len(results) == 2

    def test_empty_response(self, scanr):
        data = (FIXTURES_DIR / "empty.json").read_text()
        results = scanr.response(MockResponse(data))
        assert results == []

    def test_url_built_from_id(self, scanr):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = scanr.response(MockResponse(data))
        assert results[0]["url"].endswith("/structure/2018GR01A")

    def test_logo_url_resolved_relative(self, scanr):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = scanr.response(MockResponse(data))
        # url ends with '/' and logo starts with '/', so concatenation yields double slash (upstream behavior)
        assert "logos/cnrs.png" in results[0]["thumbnail"]
        assert results[0]["thumbnail"].startswith("https://scanr.enseignementsup-recherche.gouv.fr")
        assert results[1]["thumbnail"] is None

    def test_highlight_html_stripped(self, scanr):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = scanr.response(MockResponse(data))
        assert "<em>" not in results[0]["content"]
        assert "CNRS" in results[0]["content"]

    def test_request_post_json(self, scanr):
        params = {"pageno": 1, "headers": {}}
        scanr.request("cnrs", params)
        assert params["method"] == "POST"
        assert "cnrs" in params["data"]
