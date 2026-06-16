"""Parser fixture tests for PDBe engine."""

import json
from pathlib import Path

import pytest

from scoutlet.engine_loader import load_engine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "engines" / "pdbe"


class MockResponse:
    def __init__(self, text: str, url: str = "https://www.ebi.ac.uk/pdbe/search/pdb/select"):
        self.text = text
        self.url = url
        self.status_code = 200


@pytest.fixture
def pdbe():
    return load_engine("pdbe")


class TestPDBeParser:
    def test_skips_unpublished(self, pdbe):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pdbe.response(MockResponse(data))
        # 4 entries: REL, REL, HOLD (skipped), OBS (kept)
        assert len(results) == 3

    def test_result_url(self, pdbe):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pdbe.response(MockResponse(data))
        assert results[0]["url"] == "https://www.ebi.ac.uk/pdbe/entry/pdb/1CRN"

    def test_thumbnail_built_from_pdb_id(self, pdbe):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pdbe.response(MockResponse(data))
        assert "1CRN" in results[0]["thumbnail"]
        assert results[0]["thumbnail"].endswith(".png")

    def test_obsolete_marked_in_title(self, pdbe):
        data = (FIXTURES_DIR / "success.json").read_text()
        results = pdbe.response(MockResponse(data))
        obsolete = [r for r in results if "OBSOLETE" in r["title"]]
        assert len(obsolete) == 1
        assert "superseded" in obsolete[0]["content"].lower()

    def test_request_uses_post(self, pdbe):
        params = {"pageno": 1, "headers": {}}
        pdbe.request("crystal", params)
        assert params["method"] == "POST"
        assert params["data"]["q"] == "crystal"
