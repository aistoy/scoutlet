"""Client adapter interface for scoutlet HTTP layer.

Provides an abstraction over the HTTP client so engines don't depend
on a specific implementation (httpx, curl_cffi, primp, etc.).

Available backends:
  - "httpx" (default): plain httpx, no TLS fingerprint emulation
  - "fingerprint": primp-based, browser TLS fingerprint emulation via impersonate
"""

from __future__ import annotations

import typing as t
from abc import ABC, abstractmethod

import httpx

import logging

log = logging.getLogger("scoutlet.client_adapter")


class ClientAdapter(ABC):
    """Abstract HTTP client interface.

    Implementations must support GET, POST, proxy, timeout, and
    response objects with .text, .status_code, .url attributes.
    """

    @abstractmethod
    def get(self, url: str, **kwargs: t.Any) -> t.Any:
        ...

    @abstractmethod
    def post(self, url: str, **kwargs: t.Any) -> t.Any:
        ...

    @abstractmethod
    def close(self) -> None:
        ...


class HttpxAdapter(ClientAdapter):
    """Default adapter using httpx. No TLS fingerprint emulation."""

    def __init__(self, timeout: float = 10.0, proxy: str | None = None):
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout),
            headers={"Accept-Encoding": "gzip, deflate"},
            proxy=proxy,
        )

    def get(self, url: str, **kwargs: t.Any) -> httpx.Response:
        kwargs.pop("proxy", None)
        kwargs.pop("timeout", None)
        return self._client.get(url, **kwargs)

    def post(self, url: str, **kwargs: t.Any) -> httpx.Response:
        kwargs.pop("proxy", None)
        kwargs.pop("timeout", None)
        return self._client.post(url, **kwargs)

    def close(self) -> None:
        if not self._client.is_closed:
            self._client.close()


class PrimpAdapter(ClientAdapter):
    """Fingerprint adapter using primp with browser TLS impersonation.

    Impersonates a random real browser (Chrome, Firefox, Safari) with matching
    TLS cipher suites, ALPN, HTTP/2 settings, and header order. This makes
    requests indistinguishable from a real browser at the TLS layer.

    Requires: pip install scoutlet[fingerprint]
    """

    def __init__(self, timeout: float = 10.0, proxy: str | None = None):
        try:
            import primp
        except ImportError:
            raise ImportError(
                "primp is required for fingerprint adapter. "
                "Install with: pip install scoutlet[fingerprint]"
            )
        self._client = primp.Client(
            proxy=proxy,
            timeout=int(timeout),
            impersonate="random",
            impersonate_os="random",
            verify=True,
        )

    def get(self, url: str, **kwargs: t.Any) -> t.Any:
        kwargs.pop("proxy", None)
        kwargs.pop("timeout", None)
        follow_redirects = kwargs.pop("follow_redirects", True)
        headers = kwargs.pop("headers", None)
        cookies = kwargs.pop("cookies", None)
        params = {
            "method": "GET",
            "url": url,
            "follow_redirects": follow_redirects,
        }
        if headers:
            params["headers"] = headers
        if cookies:
            params["cookies"] = cookies
        return self._client.request(**params)

    def post(self, url: str, **kwargs: t.Any) -> t.Any:
        kwargs.pop("proxy", None)
        kwargs.pop("timeout", None)
        follow_redirects = kwargs.pop("follow_redirects", True)
        headers = kwargs.pop("headers", None)
        cookies = kwargs.pop("cookies", None)
        data = kwargs.pop("data", None)
        json_data = kwargs.pop("json", None)
        params = {
            "method": "POST",
            "url": url,
            "follow_redirects": follow_redirects,
        }
        if headers:
            params["headers"] = headers
        if cookies:
            params["cookies"] = cookies
        if data:
            params["content"] = data if isinstance(data, bytes) else data.encode()
        if json_data:
            params["json"] = json_data
        return self._client.request(**params)

    def close(self) -> None:
        pass


# Adapter factory — maps string names to adapter classes
_ADAPTERS: dict[str, type[ClientAdapter]] = {
    "httpx": HttpxAdapter,
    "default": HttpxAdapter,
    "fingerprint": PrimpAdapter,
}


def register_adapter(name: str, cls: type[ClientAdapter]) -> None:
    """Register a custom adapter class under a name."""
    _ADAPTERS[name] = cls


def create_adapter(
    backend: str = "default",
    **kwargs: t.Any,
) -> ClientAdapter:
    """Create an adapter instance by name.

    Args:
        backend: Adapter name ("httpx", "default", "fingerprint").
        **kwargs: Passed to the adapter constructor (timeout, proxy).
    """
    cls = _ADAPTERS.get(backend)
    if cls is None:
        raise ValueError(f"Unknown adapter backend: {backend!r}. Available: {list(_ADAPTERS.keys())}")
    return cls(**kwargs)
