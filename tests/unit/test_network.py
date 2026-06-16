"""Unit tests for network module."""

import pytest
import httpx

from scoutlet.network import raise_for_httperror
from scoutlet.exceptions import (
    SearchEngineAccessDeniedException,
    SearchEngineTooManyRequestsException,
    SearchEngineAPIException,
)


def _make_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code=status_code, request=httpx.Request("GET", "https://example.com"))


class TestRaiseForHttpError:
    def test_403_raises_access_denied(self):
        with pytest.raises(SearchEngineAccessDeniedException):
            raise_for_httperror(_make_response(403))

    def test_503_raises_access_denied(self):
        with pytest.raises(SearchEngineAccessDeniedException):
            raise_for_httperror(_make_response(503))

    def test_429_raises_too_many_requests(self):
        with pytest.raises(SearchEngineTooManyRequestsException):
            raise_for_httperror(_make_response(429))

    def test_500_raises_api_exception(self):
        with pytest.raises(SearchEngineAPIException):
            raise_for_httperror(_make_response(500))

    def test_400_raises_api_exception(self):
        with pytest.raises(SearchEngineAPIException):
            raise_for_httperror(_make_response(400))

    def test_200_no_exception(self):
        raise_for_httperror(_make_response(200))

    def test_301_no_exception(self):
        raise_for_httperror(_make_response(301))
