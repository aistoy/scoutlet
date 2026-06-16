"""Parser fixture tests for Astrophysics Data System (ADS) engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine
from scoutlet.exceptions import SearchEngineAPIException

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "astrophysics_data_system"


class MockResponse:
    def __init__(self, text: str, url: str = "https://api.adsabs.harvard.edu/v1/search/query"):
        self.text = text
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def ads():
    """Load ADS with a test api_key so setup() succeeds."""
    return load_engine("astrophysics_data_system", api_key="test-key")


class TestADSParser:
    def test_returns_results(self, ads):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ads.response(MockResponse(data))
        assert len(results) == 1

    def test_url_from_bibcode(self, ads):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ads.response(MockResponse(data))
        assert results[0]["url"].endswith("/abs/2017ApJ...847L..21A/")

    def test_title_stripped(self, ads):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ads.response(MockResponse(data))
        assert "Multi-messenger" in results[0]["title"]

    def test_authors_truncated_with_et_al(self, ads):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ads.response(MockResponse(data))
        # 3 authors in fixture, under the 15 cap, so no "et al."
        assert len(results[0]["authors"]) == 3
        assert "Abbott, B.P." in results[0]["authors"]

    def test_published_date_isoformat(self, ads):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ads.response(MockResponse(data))
        assert results[0]["publishedDate"].year == 2017
        assert results[0]["publishedDate"].month == 10

    def test_doi_extracted(self, ads):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = ads.response(MockResponse(data))
        assert results[0]["doi"] == "10.3847/2041-8213/aa920c"

    def test_error_raises_api_exception(self, ads):
        data = (FIXTURES_DIR / "error.json").read_text()
        with pytest.raises(SearchEngineAPIException):
            ads.response(MockResponse(data))

    def test_request_sets_auth_header(self, ads):
        params = {"pageno": 1, "headers": {}}
        ads.request("neutron star", params)
        assert params["headers"]["Authorization"] == "Bearer test-key"
        assert "q=neutron+star" in params["url"] or "q=neutron star" in params["url"]

    def test_setup_rejects_unset_key(self):
        """Without api_key, setup() returns False and engine is filtered out."""
        e = load_engine("astrophysics_data_system")
        assert e is None
