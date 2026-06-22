"""Unit tests for SearchResponse and its contained types."""

import pytest

from scoutlet.outcome import FailureKind
from scoutlet.response import EngineRunInfo, SearchResponse, SkippedEngine
from scoutlet.result_types import SearchResult


class TestEngineRunInfo:
    def test_as_dict_serializes_status_enum(self):
        info = EngineRunInfo(
            name="google",
            status=FailureKind.ANTI_BOT,
            elapsed_ms=42,
            error="CAPTCHA",
        )
        d = info.as_dict()
        assert d == {
            "name": "google",
            "status": "anti_bot",
            "elapsed_ms": 42,
            "error": "CAPTCHA",
        }

    def test_error_defaults_to_none(self):
        info = EngineRunInfo(name="bing", status=FailureKind.SUCCESS, elapsed_ms=10)
        assert info.error is None
        assert info.as_dict()["error"] is None


class TestSkippedEngine:
    def test_as_dict(self):
        s = SkippedEngine(name="google", reason="cooldown")
        assert s.as_dict() == {"name": "google", "reason": "cooldown"}


class TestSearchResponse:
    def test_empty_response(self):
        r = SearchResponse()
        assert r.results == []
        assert r.engines == []
        assert r.skipped == []
        assert r.failed == []

    def test_failed_property_filters_non_success(self):
        response = SearchResponse(
            engines=[
                EngineRunInfo(name="google", status=FailureKind.SUCCESS, elapsed_ms=10),
                EngineRunInfo(name="bing", status=FailureKind.ANTI_BOT, elapsed_ms=20, error="x"),
                EngineRunInfo(name="ddg", status=FailureKind.TIMEOUT, elapsed_ms=5000),
                EngineRunInfo(name="brave", status=FailureKind.EMPTY, elapsed_ms=30),
            ]
        )
        failed = response.failed
        assert {f.name for f in failed} == {"bing", "ddg", "brave"}
        assert "google" not in {f.name for f in failed}

    def test_as_dict_round_trip(self):
        r = SearchResponse(
            results=[
                SearchResult(url="https://x.com", title="X"),
                SearchResult(url="https://y.com", title="Y"),
            ],
            engines=[
                EngineRunInfo(name="google", status=FailureKind.SUCCESS, elapsed_ms=10),
            ],
            skipped=[
                SkippedEngine(name="flaky", reason="cooldown"),
            ],
        )
        d = r.as_dict()
        assert isinstance(d["results"], list)
        assert len(d["results"]) == 2
        assert d["results"][0]["url"] == "https://x.com"
        assert d["engines"][0]["status"] == "success"
        assert d["skipped"][0] == {"name": "flaky", "reason": "cooldown"}

    def test_as_dict_serializes_for_json(self):
        """as_dict output must be JSON-serializable (no enums, sets, datetimes)."""
        import json
        r = SearchResponse(
            results=[SearchResult(url="https://x.com", title="X", engine="google")],
            engines=[
                EngineRunInfo(name="google", status=FailureKind.PARSER_ERROR, elapsed_ms=5),
            ],
            skipped=[SkippedEngine(name="baidu", reason="not_loaded")],
        )
        # Must not raise
        json.dumps(r.as_dict())

    def test_default_lists_are_independent_per_instance(self):
        a = SearchResponse()
        b = SearchResponse()
        a.results.append(SearchResult(url="https://x.com", title="X"))
        a.engines.append(EngineRunInfo(name="x", status=FailureKind.SUCCESS, elapsed_ms=0))
        a.skipped.append(SkippedEngine(name="y", reason="z"))
        assert b.results == []
        assert b.engines == []
        assert b.skipped == []
