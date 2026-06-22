"""Unit tests for EngineOutcome and failure classification."""

import httpx
import pytest

from scoutlet.exceptions import (
    SearchEngineAccessDeniedException,
    SearchEngineAPIException,
    SearchEngineCaptchaException,
    SearchEngineTooManyRequestsException,
    SearchEngineXPathException,
    SearchXPathSyntaxException,
)
from scoutlet.outcome import (
    EngineOutcome,
    FailureKind,
    classify_failure,
)


class TestClassifyFailure:
    # --- Engine-specific anti-bot ---

    def test_captcha_is_anti_bot(self):
        exc = SearchEngineCaptchaException()
        assert classify_failure(exc) == FailureKind.ANTI_BOT

    def test_access_denied_is_anti_bot(self):
        # Generic AccessDenied (403/503) — not a Captcha, not a 429
        exc = SearchEngineAccessDeniedException()
        assert classify_failure(exc) == FailureKind.ANTI_BOT

    def test_too_many_requests_is_rate_limit(self):
        exc = SearchEngineTooManyRequestsException()
        assert classify_failure(exc) == FailureKind.RATE_LIMIT

    def test_captcha_not_misclassified_as_rate_limit(self):
        # Captcha subclasses AccessDenied too — verify ordering doesn't trip
        exc = SearchEngineCaptchaException()
        assert classify_failure(exc) != FailureKind.RATE_LIMIT

    # --- HTTP transport errors ---

    def test_connect_timeout_is_timeout(self):
        exc = httpx.ConnectTimeout("connect timed out")
        assert classify_failure(exc) == FailureKind.TIMEOUT

    def test_read_timeout_is_timeout(self):
        exc = httpx.ReadTimeout("read timed out")
        assert classify_failure(exc) == FailureKind.TIMEOUT

    def test_connect_error_is_http_error(self):
        exc = httpx.ConnectError("connection refused")
        assert classify_failure(exc) == FailureKind.HTTP_ERROR

    def test_api_exception_is_http_error(self):
        exc = SearchEngineAPIException("HTTP 500")
        assert classify_failure(exc) == FailureKind.HTTP_ERROR

    # --- Phase fallback for unknown exceptions ---

    def test_unknown_in_request_phase_is_config_error(self):
        exc = ValueError("missing api_key")
        assert classify_failure(exc, phase="request") == FailureKind.CONFIG_ERROR

    def test_unknown_in_response_phase_is_parser_error(self):
        exc = ValueError("xpath returned no nodes")
        assert classify_failure(exc, phase="response") == FailureKind.PARSER_ERROR

    def test_unknown_in_fetch_phase_is_parser_error(self):
        # Phase fallback only special-cases "request"; everything else defaults
        # to PARSER_ERROR since fetch-phase errors are usually caught by the
        # specific httpx/exception branches above.
        exc = RuntimeError("something weird")
        assert classify_failure(exc, phase="fetch") == FailureKind.PARSER_ERROR

    def test_unknown_in_unknown_phase_is_parser_error(self):
        exc = RuntimeError("???")
        assert classify_failure(exc) == FailureKind.PARSER_ERROR

    def test_xpath_syntax_exception_in_request_is_config(self):
        # Programmer error in engine module definition
        exc = SearchXPathSyntaxException("//foo[]", "unexpected token")
        assert classify_failure(exc, phase="request") == FailureKind.CONFIG_ERROR


class TestEngineOutcome:
    def test_success_outcome_ok(self):
        from scoutlet.result_types import SearchResult
        r = SearchResult(url="https://example.com", title="Example")
        outcome = EngineOutcome(
            engine="google",
            status=FailureKind.SUCCESS,
            elapsed_ms=42,
            results=[r],
        )
        assert outcome.ok is True
        assert len(outcome.results) == 1

    def test_failure_outcome_not_ok(self):
        outcome = EngineOutcome(
            engine="google",
            status=FailureKind.ANTI_BOT,
            elapsed_ms=100,
            error="CAPTCHA detected",
        )
        assert outcome.ok is False
        assert outcome.results == []
        assert outcome.error == "CAPTCHA detected"

    def test_empty_outcome_has_no_error_by_default(self):
        outcome = EngineOutcome(
            engine="mwmbl",
            status=FailureKind.EMPTY,
            elapsed_ms=5,
        )
        assert outcome.ok is False
        assert outcome.results == []
        assert outcome.error is None

    def test_default_results_is_fresh_list_per_instance(self):
        # default_factory=list must not share state across instances
        a = EngineOutcome(engine="a", status=FailureKind.EMPTY, elapsed_ms=0)
        b = EngineOutcome(engine="b", status=FailureKind.EMPTY, elapsed_ms=0)
        a.results.append("x")  # type: ignore[arg-type]
        assert b.results == []
