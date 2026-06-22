"""Search pipeline for scoutlet.

Orchestrates: build params → concurrent engine execution → aggregate results.
"""

from __future__ import annotations

import asyncio
import re
import typing as t

import httpx

from scoutlet import engine_loader
from scoutlet.result_types import SearchResult
from scoutlet.result_aggregation import ResultContainer
from scoutlet.utils import gen_useragent
from scoutlet import network

import logging

log = logging.getLogger("scoutlet.search")


# Default engine sets used when neither `engines=` nor `categories=` is given.
# Targeted at human users running CLI/WebUI without args; agents are expected
# to pass explicit engines (see docs/agent_guide.md).
DEFAULT_ENGINES_BASE = ("google", "bing", "mwmbl", "marginalia")
DEFAULT_ENGINES_ZH_EXTRA = ("baidu", "sogou", "brave")
DEFAULT_ENGINES_NONZH_EXTRA = ("brave", "yahoo", "duckduckgo")

_HAN_RE = re.compile(r"[一-鿿]")
_KANA_RE = re.compile(r"[぀-ヿ]")
_HANGUL_RE = re.compile(r"[가-힯]")


def _is_chinese_query(query: str) -> bool:
    """Return True when the query is likely Chinese (Han, no kana/hangul).

    Han characters appear in both Chinese and Japanese; requiring the absence
    of kana/hangul filters out Japanese/Korean. Pure-ASCII queries return
    False (fall through to the non-Chinese default).
    """
    if not query:
        return False
    return bool(_HAN_RE.search(query)) and not _KANA_RE.search(query) and not _HANGUL_RE.search(query)


def _resolve_default_engines(query: str) -> list[str]:
    """Pick the default engine list based on query language."""
    extra = DEFAULT_ENGINES_ZH_EXTRA if _is_chinese_query(query) else DEFAULT_ENGINES_NONZH_EXTRA
    return list(DEFAULT_ENGINES_BASE) + list(extra)


def _build_default_params(
    query: str,
    pageno: int = 1,
    language: str = "all",
    time_range: str | None = None,
    safesearch: int = 0,
    timeout: float = 10.0,
    proxy: str | None = None,
) -> dict[str, t.Any]:
    """Build default request parameters, similar to SearXNG's OnlineProcessor.get_params."""
    return {
        "method": "GET",
        "headers": {
            "User-Agent": gen_useragent(),
            "Accept-Language": "en,en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "no-cache",
            "DNT": "1",
            "Connection": "keep-alive",
        },
        "data": {},
        "json": {},
        "url": "",
        "cookies": {},
        "auth": None,
        "allow_redirects": True,
        "query": query,
        "pageno": pageno,
        "language": language,
        "searxng_locale": language,
        "time_range": time_range or "",
        "safesearch": safesearch,
        "timeout": timeout,
        "proxy": proxy,
        "engine_data": {},
        "raise_for_httperror": False,
    }


def _run_engine(
    engine,
    params: dict[str, t.Any],
    adapter_backend: str | None = None,
) -> list[SearchResult]:
    """Run a single engine search synchronously.

    Follows SearXNG's pattern:
    1. Call engine.request(query, params) → engine fills URL/headers
    2. Send HTTP request
    3. Call engine.response(resp) → engine parses and returns results

    Per-engine failures are logged and returned as an empty list so that one
    broken engine doesn't abort the whole search. Callers that need the
    structured failure signal should wrap this themselves.
    """
    engine_name = engine.name

    def _parse_response(resp, params):
        # Wrap response to guarantee search_params attribute (primp Response is slotted)
        if not hasattr(resp, 'search_params'):
            class _RespWrapper:
                __slots__ = ('_resp', 'search_params')
                def __init__(self, r):
                    self._resp = r
                    self.search_params = None
                def __getattr__(self, name):
                    return getattr(self._resp, name)
            wrapped = _RespWrapper(resp)
            wrapped.search_params = params
            resp = wrapped
        else:
            resp.search_params = params
        results = engine.response(resp)
        normalized = []
        for r in results:
            if isinstance(r, dict):
                normalized.append(SearchResult(**{k: v for k, v in r.items()
                                                  if k in SearchResult.__dataclass_fields__}))
            elif isinstance(r, SearchResult):
                normalized.append(r)
            else:
                log.warning("Engine %s returned unexpected type: %s", engine_name, type(r))
        return normalized

    try:
        # Step 1: Engine builds request params
        result = engine.request(params.get("query", ""), params)
        if result is not None:
            params = result

        if not params.get("url"):
            return []

        # Step 2: Send HTTP request
        method = params.get("method", "GET").upper()
        url = params["url"]
        headers = params.get("headers", {})
        cookies = params.get("cookies", {})
        timeout = params.get("timeout", 10.0)
        proxy = params.get("proxy")
        follow_redirects = params.get("allow_redirects", True)

        # Build network kwargs with optional per-engine adapter
        net_kwargs = dict(
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            follow_redirects=follow_redirects,
        )
        if adapter_backend:
            net_kwargs["adapter_backend"] = adapter_backend

        if method == "POST":
            data = params.get("data")
            json_data = params.get("json")
            resp = network.post(
                url,
                data=data if data else None,
                json=json_data if json_data else None,
                **net_kwargs,
            )
        else:
            resp = network.get(url, **net_kwargs)

        # Check for HTTP errors if engine requested it
        if params.get("raise_for_httperror"):
            network.raise_for_httperror(resp)

        # Step 3: Engine parses response
        return _parse_response(resp, params)

    except Exception as e:
        log.warning("Engine '%s' failed: %s", engine_name, e)
        return []


async def search(
    query: str,
    engines: list[str] | None = None,
    categories: list[str] | None = None,
    pageno: int = 1,
    language: str = "all",
    time_range: str | None = None,
    safesearch: int = 0,
    timeout: float = 10.0,
    engine_dir: str | None = None,
    proxy: str | None = None,
    search_adapter_backend: str | None = None,
) -> list[SearchResult]:
    """Execute a search across multiple engines concurrently.

    Args:
        query: Search query string
        engines: List of engine names (e.g., ["google", "bing"]). When None
            and ``categories`` is also None, a language-aware default set is
            used (Chinese queries pick Chinese-friendly engines; otherwise an
            international set). Pass explicitly to override.
        categories: Search by category instead (e.g., ["general"]). When
            given, loads all engines in those categories. Both None triggers
            the default set above.
        pageno: Page number (1-indexed)
        language: Language code (e.g., "en", "all")
        time_range: Time filter ("day", "week", "month", "year")
        safesearch: Safe search level (0, 1, 2)
        timeout: Per-engine timeout in seconds
        engine_dir: Custom engine directory
        proxy: HTTP/SOCKS5 proxy URL (e.g., "socks5://127.0.0.1:1080")
        search_adapter_backend: Global HTTP adapter backend ("httpx" or
            "fingerprint"). Per-engine ``http_client`` overrides this.

    Returns:
        List of aggregated, sorted SearchResult objects
    """
    # Resolve engines to load
    if engines:
        engine_names = engines
    elif categories:
        # Explicit category-based loading: peek each engine's categories
        # without running setup() to avoid noise from unrelated engines
        # (spotify, youtube_api, etc.).
        engine_names = []
        for name in engine_loader.list_available_engines(engine_dir):
            cats = engine_loader.peek_engine_categories(name, engine_dir)
            if any(c in cats for c in categories):
                engine_names.append(name)
    else:
        # No engines, no categories → language-aware default for human users.
        # Designed for CLI/WebUI; agents should pass engines explicitly.
        engine_names = _resolve_default_engines(query)
        log.debug(
            "Default engine set for query %r (chinese=%s): %s",
            query, _is_chinese_query(query), engine_names,
        )

    # Load engines that are not already in the registry
    missing = [n for n in engine_names if n not in engine_loader.engines]
    if missing or not engine_loader.engines:
        engine_loader.load_engines(
            engine_names=list(set(engine_names) | set(engine_loader.engines.keys())),
            engine_dir=engine_dir,
        )

    # Get loaded engine modules
    active_engines = []
    for name in engine_names:
        eng = engine_loader.engines.get(name)
        if eng:
            active_engines.append(eng)

    if not active_engines:
        log.warning("No engines available for search")
        return []

    # Build params for each engine
    engine_params = []
    for eng in active_engines:
        # Per-engine proxy override: engine.proxies takes precedence over global proxy
        eng_proxy = getattr(eng, 'proxies', None) or proxy
        # Per-engine adapter backend wins over the global flag; "" means unset.
        eng_adapter = getattr(eng, 'http_client', "") or search_adapter_backend
        params = _build_default_params(
            query=query,
            pageno=pageno,
            language=language,
            time_range=time_range,
            safesearch=safesearch,
            timeout=min(timeout, getattr(eng, 'timeout', 10.0)),
            proxy=eng_proxy,
        )
        engine_params.append((eng, params, eng_adapter))

    # Execute engines concurrently via threads
    async def _run_in_thread(eng, params, adapter):
        return await asyncio.to_thread(_run_engine, eng, params, adapter)

    tasks = [
        _run_in_thread(eng, params, adapter)
        for eng, params, adapter in engine_params
    ]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    container = ResultContainer(engines_registry=engine_loader.engines)
    for (eng, *_), results in zip(engine_params, results_list):
        if isinstance(results, Exception):
            log.warning("Engine '%s' raised: %s", eng.name, results)
            continue
        if results:
            container.extend(eng.name, results)

    container.close()
    return container.get_ordered_results()


def search_sync(
    query: str,
    engines: list[str] | None = None,
    categories: list[str] | None = None,
    pageno: int = 1,
    language: str = "all",
    time_range: str | None = None,
    safesearch: int = 0,
    timeout: float = 10.0,
    engine_dir: str | None = None,
    proxy: str | None = None,
    search_adapter_backend: str | None = None,
) -> list[SearchResult]:
    """Synchronous wrapper for search()."""
    return asyncio.run(search(
        query=query,
        engines=engines,
        categories=categories,
        pageno=pageno,
        language=language,
        time_range=time_range,
        safesearch=safesearch,
        timeout=timeout,
        engine_dir=engine_dir,
        proxy=proxy,
        search_adapter_backend=search_adapter_backend,
    ))
