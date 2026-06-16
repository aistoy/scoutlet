"""Parser fixture tests for PyPI engine."""

from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "pypi"


class MockResponse:
    def __init__(self, text: str, url: str = "https://pypi.org/search/?q=test"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def pypi():
    return load_engine("pypi")


class TestPyPIParser:
    def test_returns_results(self, pypi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = pypi.response(MockResponse(html))
        assert len(results) == 2

    def test_result_url(self, pypi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = pypi.response(MockResponse(html))
        assert results[0]["url"] == "https://pypi.org/project/requests/"
        assert results[1]["url"] == "https://pypi.org/project/httpx/"

    def test_result_title_and_version(self, pypi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = pypi.response(MockResponse(html))
        assert results[0]["title"] == "requests"
        assert results[0]["version"] == "2.31.0"

    def test_result_published_date(self, pypi):
        html = (FIXTURES_DIR / "success.html").read_text()
        results = pypi.response(MockResponse(html))
        assert results[0]["publishedDate"].year == 2023

    def test_request_builds_url(self, pypi):
        params = {"pageno": 1}
        pypi.request("httpx", params)
        assert "q=httpx" in params["url"]
        assert "pypi.org/search/" in params["url"]
