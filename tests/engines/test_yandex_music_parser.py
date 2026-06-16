"""Parser fixture tests for Yandex Music engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "yandex_music"


class MockResponse:
    def __init__(self, text, url="https://music.yandex.ru/handlers/music-search.jsx"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def yandex_music():
    return load_engine("yandex_music")


class TestYandexMusicParser:
    def test_filters_to_music_type(self, yandex_music):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = yandex_music.response(MockResponse(data))
        # 3 items: 2 music, 1 podcast (skipped)
        assert len(results) == 2

    def test_url(self, yandex_music):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = yandex_music.response(MockResponse(data))
        assert results[0]["url"] == "https://music.yandex.ru/album/album456/track/track123"

    def test_iframe_src(self, yandex_music):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = yandex_music.response(MockResponse(data))
        assert "/iframe/track/track123/album456" in results[0]["iframe_src"]

    def test_content_format(self, yandex_music):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = yandex_music.response(MockResponse(data))
        assert "[Russian Album]" in results[0]["content"]
        assert "Russian Artist" in results[0]["content"]
