"""Parser fixture tests for IMDB engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "imdb"


class MockResponse:
    def __init__(self, text, url="https://v2.sg.media-imdb.com/suggestion"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def imdb():
    return load_engine("imdb")


class TestImdbParser:
    def test_skips_unknown_category(self, imdb):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = imdb.response(MockResponse(data))
        # 3 entries, 1 has unknown prefix (xx)
        assert len(results) == 2

    def test_title_url_by_category(self, imdb):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = imdb.response(MockResponse(data))
        assert results[0]["url"] == "https://imdb.com/title/tt1375666"
        assert results[1]["url"] == "https://imdb.com/name/nm0000138"

    def test_title_includes_year(self, imdb):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = imdb.response(MockResponse(data))
        assert "Inception (2010)" in results[0]["title"]

    def test_thumbnail_includes_magic_resize(self, imdb):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = imdb.response(MockResponse(data))
        assert "QL75_UX280" in results[0]["thumbnail"]

    def test_content_combines_rank_year_stars(self, imdb):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = imdb.response(MockResponse(data))
        content = results[0]["content"]
        assert "(1)" in content
        assert "2010" in content
        assert "Leonardo DiCaprio" in content
