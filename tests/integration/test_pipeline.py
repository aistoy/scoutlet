"""Mock-HTTP integration tests for the search pipeline.

Each test drives ``search_sync()`` through the full
``engine.request() → network.get() → engine.response() → classify → health.update``
chain, with respx scripting the HTTP layer. This is the middle layer
between parser fixture tests (which skip ``request()``) and live tests
(which depend on real sites).
"""

from __future__ import annotations

import httpx
import pytest

from scoutlet import engine_loader
from scoutlet.health import get_default_registry
from scoutlet.outcome import FailureKind
from scoutlet.pipeline import search_sync


# ---------------------------------------------------------------------------
# Happy path: verifies engine.request() builds a real URL and the full
# chain (fetch + parse + aggregate) works end-to-end.
# ---------------------------------------------------------------------------


def test_happy_path_returns_results(respx_mock, bing_success_html):
    respx_mock.route(url__startswith="https://www.bing.com/search").mock(
        return_value=httpx.Response(200, text=bing_success_html)
    )

    response = search_sync("python tutorial", engines=["bing"])

    assert response.engines[0].status == FailureKind.SUCCESS
    assert len(response.results) >= 1
    for r in response.results:
        assert r.url
        assert r.title
        assert r.score > 0

    # Coverage gap this closes: engine.request() actually built a URL
    # with the query in it. No other test in the repo verifies this.
    assert len(respx_mock.calls) == 1
    request_url = respx_mock.calls[0].request.url
    assert "bing.com/search" in str(request_url)
    assert request_url.params["q"] == "python tutorial"


# ---------------------------------------------------------------------------
# Exception classification: verifies _run_engine's try/except wiring and
# classify_failure() mapping for transport-layer failures.
# ---------------------------------------------------------------------------


def test_timeout_classified(respx_mock):
    respx_mock.route(url__startswith="https://www.bing.com/search").mock(
        side_effect=httpx.TimeoutException("read timed out")
    )

    response = search_sync("python tutorial", engines=["bing"])

    assert response.engines[0].status == FailureKind.TIMEOUT
    assert response.results == []


def test_connection_error_classified(respx_mock):
    respx_mock.route(url__startswith="https://www.bing.com/search").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    response = search_sync("python tutorial", engines=["bing"])

    assert response.engines[0].status == FailureKind.HTTP_ERROR
    assert response.results == []


# ---------------------------------------------------------------------------
# Engine opt-out: engine.request() returns None → _run_engine sees no URL
# and returns EMPTY without ever hitting the network.
# ---------------------------------------------------------------------------


def test_engine_opt_out_returns_empty(respx_mock, monkeypatch):
    engine_loader.load_engines(["bing"])
    bing = engine_loader.engines["bing"]
    monkeypatch.setattr(bing, "request", lambda query, params: None)

    response = search_sync("python tutorial", engines=["bing"])

    assert response.engines[0].status == FailureKind.EMPTY
    assert len(respx_mock.calls) == 0


# ---------------------------------------------------------------------------
# Rate limit → cooldown → subsequent skip. This is the marquee test:
# verifies the health registry, the skip-filter in search(), and the
# SkippedEngine wiring all compose correctly end-to-end.
#
# Uses Wikipedia because it sets raise_for_httperror=True; Bing does not,
# so Bing's failure path stops at EMPTY (parsed 0 results).
# ---------------------------------------------------------------------------


def test_rate_limit_triggers_cooldown_and_skip(respx_mock):
    respx_mock.route(url__startswith="https://en.wikipedia.org/w/api.php").mock(
        return_value=httpx.Response(429)
    )

    first = search_sync("python", engines=["wikipedia"])
    assert first.engines[0].status == FailureKind.RATE_LIMIT
    assert get_default_registry().is_available("wikipedia") is False

    # Second call: Wikipedia should be filtered out before dispatch.
    second = search_sync("python", engines=["wikipedia"])
    assert second.skipped, "expected Wikipedia in skipped list"
    assert second.skipped[0].name == "wikipedia"
    assert second.skipped[0].reason == "cooldown"
    assert second.engines == []


def test_access_denied_503_classified(respx_mock):
    # network.raise_for_httperror maps 503 → AccessDenied → ANTI_BOT.
    respx_mock.route(url__startswith="https://en.wikipedia.org/w/api.php").mock(
        return_value=httpx.Response(503)
    )

    response = search_sync("python", engines=["wikipedia"])

    assert response.engines[0].status == FailureKind.ANTI_BOT
    assert get_default_registry().is_available("wikipedia") is False


# ---------------------------------------------------------------------------
# Block-page detection: verifies response_classifier integration in
# _run_engine. CAPTCHA/blocked pages on 2xx are flagged ANTI_BOT before
# the parser runs (parser would otherwise return []). Covers three paths:
#   1. Real block page → ANTI_BOT
#   2. Empty 2xx body → falls through to parser → EMPTY (preserves §6.2 B)
#   3. Classifier raises → swallowed, search continues
# ---------------------------------------------------------------------------


def test_block_page_classified_as_anti_bot(respx_mock, bing_captcha_html):
    respx_mock.route(url__startswith="https://www.bing.com/search").mock(
        return_value=httpx.Response(200, text=bing_captcha_html)
    )

    response = search_sync("python tutorial", engines=["bing"])

    assert response.engines[0].status == FailureKind.ANTI_BOT
    assert response.results == []
    assert "Block page" in (response.engines[0].error or "")


def test_empty_body_not_flagged_as_anti_bot(respx_mock):
    # An empty 2xx body should NOT be flagged ANTI_BOT. What happens after
    # (parser returns EMPTY or raises PARSER_ERROR) is engine-specific;
    # the invariant this test guards is "empty ≠ anti_bot", which keeps
    # §6.2 B (normal empty results must not trigger cooldown).
    respx_mock.route(url__startswith="https://www.bing.com/search").mock(
        return_value=httpx.Response(200, text="")
    )

    response = search_sync("python tutorial", engines=["bing"])

    assert response.engines[0].status != FailureKind.ANTI_BOT
    assert response.results == []


def test_block_classifier_failure_does_not_break_search(
    respx_mock, bing_success_html, monkeypatch,
):
    # A buggy classifier should not abort the pipeline. The engine should
    # still parse results normally.
    import scoutlet.pipeline as pipeline_module

    def _broken_classifier(html, url=""):
        raise RuntimeError("classifier bug")

    monkeypatch.setattr(pipeline_module, "detect_block_page", _broken_classifier)

    respx_mock.route(url__startswith="https://www.bing.com/search").mock(
        return_value=httpx.Response(200, text=bing_success_html)
    )

    response = search_sync("python tutorial", engines=["bing"])

    assert response.engines[0].status == FailureKind.SUCCESS
    assert len(response.results) >= 1


# ---------------------------------------------------------------------------
# Top-level response shape: query is echoed, status reflects the mix of
# engine outcomes. Covers §6.2 D wiring.
# ---------------------------------------------------------------------------


def test_response_query_is_echoed(respx_mock, bing_success_html):
    respx_mock.route(url__startswith="https://www.bing.com/search").mock(
        return_value=httpx.Response(200, text=bing_success_html)
    )

    response = search_sync("python tutorial", engines=["bing"])
    assert response.query == "python tutorial"
    assert response.as_dict()["query"] == "python tutorial"


def test_response_status_success_when_all_engines_succeed(respx_mock, bing_success_html):
    from scoutlet.response import SearchStatus

    respx_mock.route(url__startswith="https://www.bing.com/search").mock(
        return_value=httpx.Response(200, text=bing_success_html)
    )

    response = search_sync("python tutorial", engines=["bing"])
    assert response.status == SearchStatus.SUCCESS


def test_response_status_partial_when_one_engine_fails(respx_mock, bing_success_html):
    from scoutlet.response import SearchStatus

    # Bing succeeds, wikipedia (raise_for_httperror=True) returns 503.
    respx_mock.route(url__startswith="https://www.bing.com/search").mock(
        return_value=httpx.Response(200, text=bing_success_html)
    )
    respx_mock.route(url__startswith="https://en.wikipedia.org/w/api.php").mock(
        return_value=httpx.Response(503)
    )

    response = search_sync("python", engines=["bing", "wikipedia"])
    assert response.status == SearchStatus.PARTIAL


def test_response_status_failed_when_all_engines_fail(respx_mock):
    from scoutlet.response import SearchStatus

    respx_mock.route(url__startswith="https://en.wikipedia.org/w/api.php").mock(
        return_value=httpx.Response(503)
    )

    response = search_sync("python", engines=["wikipedia"])
    assert response.status == SearchStatus.FAILED
    assert response.results == []
