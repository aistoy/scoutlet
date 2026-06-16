"""Parser fixture tests for Lemmy (Communities) engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "lemmy"


class MockResponse:
    def __init__(self, text, url="https://lemmy.ml/api/v3/search"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def lemmy():
    return load_engine("lemmy")


class TestLemmyParser:
    def test_returns_results(self, lemmy):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = lemmy.response(MockResponse(data))
        assert len(results) == 2

    def test_url(self, lemmy):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = lemmy.response(MockResponse(data))
        assert results[0]["url"] == "https://lemmy.ml/c/technology"

    def test_markdown_stripped(self, lemmy):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = lemmy.response(MockResponse(data))
        # Description had **News** and *discussion*; should be stripped
        assert "News" in results[0]["content"]
        assert "**" not in results[0]["content"]
        assert "*" not in results[0]["content"]

    def test_markdown_link_simplified(self, lemmy):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = lemmy.response(MockResponse(data))
        # [Science](url) -> Science
        assert "Science" in results[1]["content"]
        assert "](" not in results[1]["content"]

    def test_published_date_parsed(self, lemmy):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = lemmy.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2020

    def test_metadata_includes_counts(self, lemmy):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = lemmy.response(MockResponse(data))
        md = results[0]["metadata"]
        assert "subscribers: 12500" in md
        assert "posts: 4500" in md
