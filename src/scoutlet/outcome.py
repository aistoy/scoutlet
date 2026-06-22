"""Structured engine execution outcome.

`_run_engine` returns `EngineOutcome` instead of a bare `list[SearchResult]`
so downstream consumers (health registry, routing, auto-heal) can tell
"engine got CAPTCHA'd" apart from "engine parser broke" apart from
"engine returned 0 results".

The public `search()` / `search_sync()` API still returns `list[SearchResult]`;
EngineOutcome is internal.
"""

from __future__ import annotations

import enum
import typing as t
from dataclasses import dataclass, field

import httpx

from scoutlet.exceptions import (
    SearchEngineAccessDeniedException,
    SearchEngineCaptchaException,
    SearchEngineAPIException,
    SearchEngineTooManyRequestsException,
)
from scoutlet.result_types import SearchResult


class FailureKind(enum.Enum):
    SUCCESS = "success"
    EMPTY = "empty"                # 200 OK but 0 parsed results (or engine declined)
    ANTI_BOT = "anti_bot"          # CAPTCHA / AccessDenied / Cloudflare-style block
    RATE_LIMIT = "rate_limit"      # 429
    HTTP_ERROR = "http_error"      # other 4xx/5xx or transport error
    PARSER_ERROR = "parser_error"  # engine.response() raised
    TIMEOUT = "timeout"
    CONFIG_ERROR = "config_error"  # engine.request() raised (missing api_key, etc.)


@dataclass
class EngineOutcome:
    engine: str
    status: FailureKind
    elapsed_ms: int
    results: list[SearchResult] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == FailureKind.SUCCESS


def classify_failure(exc: BaseException, phase: str = "unknown") -> FailureKind:
    """Map an exception to FailureKind based on type and execution phase.

    Order matters: more specific subclasses checked before their parents.
    The phase ("request" / "fetch" / "response") is a fallback for exceptions
    that don't match a known scoutlet/httpx type — engine.request() failures
    default to CONFIG_ERROR, engine.response() failures to PARSER_ERROR.
    """
    if isinstance(exc, SearchEngineCaptchaException):
        return FailureKind.ANTI_BOT
    if isinstance(exc, SearchEngineTooManyRequestsException):
        return FailureKind.RATE_LIMIT
    if isinstance(exc, SearchEngineAccessDeniedException):
        return FailureKind.ANTI_BOT
    if isinstance(exc, httpx.TimeoutException):
        return FailureKind.TIMEOUT
    if isinstance(exc, httpx.HTTPError):
        return FailureKind.HTTP_ERROR
    if isinstance(exc, SearchEngineAPIException):
        return FailureKind.HTTP_ERROR
    if phase == "request":
        return FailureKind.CONFIG_ERROR
    return FailureKind.PARSER_ERROR
