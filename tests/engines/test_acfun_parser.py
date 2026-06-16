"""Parser fixture tests for Acfun engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "acfun"


class MockResponse:
    def __init__(self, text, url="https://www.acfun.cn/search"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def acfun():
    return load_engine("acfun")


class TestAcfunParser:
    def test_returns_results(self, acfun):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = acfun.response(MockResponse(html))
        assert len(results) == 2

    def test_url_built_from_content_id(self, acfun):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = acfun.response(MockResponse(html))
        assert results[0]["url"] == "https://www.acfun.cn/v/ac12345"

    def test_iframe_src(self, acfun):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = acfun.response(MockResponse(html))
        assert results[0]["iframe_src"] == "https://www.acfun.cn/player/ac12345"

    def test_published_date(self, acfun):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = acfun.response(MockResponse(html))
        assert results[0]["publishedDate"].year == 2024
        assert results[0]["publishedDate"].month == 1

    def test_length_timedelta(self, acfun):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = acfun.response(MockResponse(html))
        # 3:45 = 3 minutes 45 seconds
        assert results[0]["length"].seconds == 225
