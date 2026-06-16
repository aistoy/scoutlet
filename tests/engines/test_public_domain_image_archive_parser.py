"""Parser fixture tests for Public Domain Image Archive engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "public_domain_image_archive"


class MockResponse:
    def __init__(self, text, url="https://pdimagearchive.org/api", status_code=200):
        self.text = text
        self.url = url
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def pda():
    return load_engine("public_domain_image_archive")


class TestPDAParser:
    def test_returns_results(self, pda):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pda.response(MockResponse(data))
        assert len(results) == 2

    def test_url_built_from_object_id(self, pda):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pda.response(MockResponse(data))
        assert results[0]["url"].endswith("/images/abc123")

    def test_img_src_strips_query_params(self, pda):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pda.response(MockResponse(data))
        assert "ixid" not in results[0]["img_src"]
        assert "?" not in results[0]["img_src"]

    def test_thumbnail_appends_suffix(self, pda):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pda.response(MockResponse(data))
        assert "fit=max" in results[0]["thumbnail_src"]
        assert "h=360" in results[0]["thumbnail_src"]

    def test_title_includes_artist_and_year(self, pda):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pda.response(MockResponse(data))
        assert "Leonardo da Vinci" in results[0]["title"]
        assert "1490" in results[0]["title"]
