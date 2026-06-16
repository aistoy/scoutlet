"""Parser fixture tests for MRS (Matrix Rooms Search) engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "mrs"


class MockResponse:
    def __init__(self, text, url="https://mrs-host/search"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def mrs():
    return load_engine("mrs", base_url="https://mrs.example.com")


class TestMrsParser:
    def test_returns_results(self, mrs):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mrs.response(MockResponse(data))
        assert len(results) == 2

    def test_url_built_from_alias(self, mrs):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mrs.response(MockResponse(data))
        assert results[0]["url"] == "https://matrix.to/#/#technology:matrix.org"

    def test_content_includes_members_and_server(self, mrs):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = mrs.response(MockResponse(data))
        content = results[0]["content"]
        assert "12500 members" in content
        assert "matrix.org" in content
        assert "#technology:matrix.org" in content

    def test_setup_rejects_missing_base_url(self):
        e = load_engine("mrs")
        assert e is None
