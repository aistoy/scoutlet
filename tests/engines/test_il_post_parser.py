"""Parser fixture tests for Il Post engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "il_post"


class MockResponse:
    def __init__(self, text, url="https://api.ilpost.org/search/api/site_search/"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def il_post():
    return load_engine("il_post")


class TestIlPostParser:
    def test_returns_results(self, il_post):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = il_post.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, il_post):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = il_post.response(MockResponse(data))
        assert results[0]["url"] == "https://www.ilpost.it/2024/01/15/articolo1/"

    def test_title_and_summary(self, il_post):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = il_post.response(MockResponse(data))
        assert results[0]["title"] == "Le ultime notizie"
        assert "riassunto" in results[0]["content"].lower()

    def test_thumbnail(self, il_post):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = il_post.response(MockResponse(data))
        assert results[0]["thumbnail"].endswith("news1.jpg")
        assert results[1]["thumbnail"] is None
