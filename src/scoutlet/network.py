"""HTTP client for scoutlet, thin wrapper around client adapters."""

import typing as t

from scoutlet.exceptions import (
    SearchEngineAccessDeniedException,
    SearchEngineCaptchaException,
    SearchEngineTooManyRequestsException,
    SearchEngineAPIException,
)

import logging

logger = logging.getLogger("scoutlet.network")

# Module-level adapter backend: "default" (httpx) or "fingerprint" (primp)
_adapter_backend: str = "default"

# Cache adapters by (backend, proxy) tuple
_adapters: dict[tuple[str, str | None], t.Any] = {}


def set_adapter_backend(backend: str) -> None:
    """Set the global HTTP adapter backend.

    Args:
        backend: "default" (httpx) or "fingerprint" (primp with TLS impersonation).
    """
    global _adapter_backend
    _adapter_backend = backend
    close()


def _get_adapter(
    proxy: str | None = None,
    timeout: float = 10.0,
    backend: str | None = None,
):
    """Get or create a cached adapter."""
    from scoutlet.client_adapter import create_adapter

    effective_backend = backend or _adapter_backend
    key = (effective_backend, proxy)
    adapter = _adapters.get(key)
    if adapter is None:
        adapter = create_adapter(effective_backend, timeout=timeout, proxy=proxy)
        _adapters[key] = adapter
    return adapter


def get(url: str, **kwargs: t.Any) -> t.Any:
    """Send a GET request."""
    proxy = kwargs.pop("proxy", None)
    timeout = kwargs.pop("timeout", 10.0)
    backend = kwargs.pop("adapter_backend", None)
    adapter = _get_adapter(proxy=proxy, timeout=timeout, backend=backend)
    return adapter.get(url, **kwargs)


def post(url: str, **kwargs: t.Any) -> t.Any:
    """Send a POST request."""
    proxy = kwargs.pop("proxy", None)
    timeout = kwargs.pop("timeout", 10.0)
    backend = kwargs.pop("adapter_backend", None)
    adapter = _get_adapter(proxy=proxy, timeout=timeout, backend=backend)
    return adapter.post(url, **kwargs)


def raise_for_httperror(resp) -> None:
    """Raise appropriate exception for HTTP error responses."""
    if resp.status_code in (403, 503):
        raise SearchEngineAccessDeniedException()
    if resp.status_code == 429:
        raise SearchEngineTooManyRequestsException()
    if resp.status_code >= 500:
        raise SearchEngineAPIException(f"HTTP {resp.status_code}")
    if resp.status_code >= 400:
        raise SearchEngineAPIException(f"HTTP {resp.status_code}")


def close() -> None:
    """Close all cached adapters."""
    for adapter in _adapters.values():
        try:
            adapter.close()
        except Exception:
            pass
    _adapters.clear()
