"""Unit tests for SearchResponse and its contained types."""

import pytest

from scoutlet.outcome import EngineOutcome, FailureKind
from scoutlet.response import (
    EngineRunInfo,
    SearchResponse,
    SearchStatus,
    SkippedEngine,
    compute_status,
)
from scoutlet.result_types import SearchResult


def _outcome(engine: str, status: FailureKind) -> EngineOutcome:
    return EngineOutcome(engine=engine, status=status, elapsed_ms=10)


class TestComputeStatus:
    def test_no_outcomes_no_skipped_is_success(self):
        # Vacuous call: nothing ran, nothing skipped. Not a failure.
        assert compute_status([], []) == SearchStatus.SUCCESS

    def test_all_success_is_success(self):
        outcomes = [
            _outcome("a", FailureKind.SUCCESS),
            _outcome("b", FailureKind.SUCCESS),
        ]
        assert compute_status(outcomes, []) == SearchStatus.SUCCESS

    def test_empty_counts_as_success(self):
        # §6.2 B: EMPTY is a valid outcome, not a failure.
        outcomes = [
            _outcome("a", FailureKind.SUCCESS),
            _outcome("b", FailureKind.EMPTY),
        ]
        assert compute_status(outcomes, []) == SearchStatus.SUCCESS

    def test_mixed_success_and_failure_is_partial(self):
        outcomes = [
            _outcome("a", FailureKind.SUCCESS),
            _outcome("b", FailureKind.TIMEOUT),
        ]
        assert compute_status(outcomes, []) == SearchStatus.PARTIAL

    def test_success_with_skipped_is_partial(self):
        outcomes = [_outcome("a", FailureKind.SUCCESS)]
        skipped = [SkippedEngine(name="b", reason="cooldown")]
        assert compute_status(outcomes, skipped) == SearchStatus.PARTIAL

    def test_all_failed_is_failed(self):
        outcomes = [
            _outcome("a", FailureKind.TIMEOUT),
            _outcome("b", FailureKind.ANTI_BOT),
        ]
        assert compute_status(outcomes, []) == SearchStatus.FAILED

    def test_all_skipped_is_failed(self):
        skipped = [SkippedEngine(name="a", reason="cooldown")]
        assert compute_status([], skipped) == SearchStatus.FAILED

    def test_empty_with_failure_is_partial(self):
        outcomes = [
            _outcome("a", FailureKind.EMPTY),
            _outcome("b", FailureKind.TIMEOUT),
        ]
        # EMPTY counts as success-equivalent, so this is mixed → PARTIAL.
        assert compute_status(outcomes, []) == SearchStatus.PARTIAL


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
        a.warnings.append("be careful")
        assert b.results == []
        assert b.engines == []
        assert b.skipped == []
        assert b.warnings == []

    def test_as_dict_includes_query_status_warnings(self):
        r = SearchResponse(
            query="python tutorial",
            status=SearchStatus.PARTIAL,
            warnings=["engine bing timed out"],
        )
        d = r.as_dict()
        assert d["query"] == "python tutorial"
        assert d["status"] == "partial"
        assert d["warnings"] == ["engine bing timed out"]
