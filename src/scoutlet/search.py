"""Search pipeline for scoutlet.

Orchestrates: build params → concurrent engine execution → aggregate results.
"""

from __future__ import annotations

import asyncio
import typing as t

import httpx

from scoutlet import engine_loader
from scoutlet.result_types import SearchResult
from scoutlet.result_aggregation import ResultContainer
from scoutlet.utils import gen_useragent
from scoutlet import network

import logging

log = logging.getLogger("scoutlet.search")


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
    fallback_to_browser: bool = False,
    cdp_endpoint: str = "http://localhost:9222",
    auto_launch_browser: bool = False,
    headless: bool = True,
    browser_args: list[str] | None = None,
    block_resources: bool = True,
    adapter_backend: str | None = None,
) -> list[SearchResult]:
    """Run a single engine search synchronously.

    Follows SearXNG's pattern:
    1. Call engine.request(query, params) → engine fills URL/headers
    2. Send HTTP request
    3. Call engine.response(resp) → engine parses and returns results

    If fallback_to_browser=True and HTTP fails with CAPTCHA/AccessDenied,
    retry via CDP browser connection.
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
        # Check if we should fallback to browser
        should_fallback = fallback_to_browser and isinstance(e, (
            network.SearchEngineCaptchaException,
            network.SearchEngineAccessDeniedException,
            network.SearchEngineTooManyRequestsException,
        ))

        if should_fallback:
            log.warning(
                "Engine '%s' HTTP failed (%s), retrying via CDP browser",
                engine_name, e,
            )
            try:
                from scoutlet import browser
                html, status = browser.run_via_cdp(
                    url=params["url"],
                    method=params.get("method", "GET").upper(),
                    post_data=params.get("data"),
                    headers=headers,
                    cdp_endpoint=cdp_endpoint,
                    timeout=timeout,
                    auto_launch_browser=auto_launch_browser,
                    headless=headless,
                    browser_args=browser_args,
                    block_resources=block_resources,
                )

                # Build a mock response object for the engine's response() parser
                class MockResponse:
                    status_code = status
                    text = html
                    url = params["url"]
                    search_params = params

                return _parse_response(MockResponse(), params)

            except Exception as cdp_err:
                log.warning(
                    "Engine '%s' CDP fallback also failed: %s",
                    engine_name, cdp_err,
                )

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
) -> list[SearchResult]:
    """Execute a search across multiple engines concurrently.

    Args:
        query: Search query string
        engines: List of engine names (e.g., ["google", "bing"])
        categories: Search by category instead (e.g., ["general"])
        pageno: Page number (1-indexed)
        language: Language code (e.g., "en", "all")
        time_range: Time filter ("day", "week", "month", "year")
        safesearch: Safe search level (0, 1, 2)
        timeout: Per-engine timeout in seconds
        engine_dir: Custom engine directory
        proxy: HTTP/SOCKS5 proxy URL (e.g., "socks5://127.0.0.1:1080")

    Returns:
        List of aggregated, sorted SearchResult objects
    """
    # Resolve engines to load
    if engines:
        engine_names = engines
    elif categories:
        # Peek each engine's categories without running setup(), then load only
        # matches — avoids setup() noise from unrelated engines (e.g., spotify,
        # youtube_api) when the user asked for a specific category.
        engine_names = []
        for name in engine_loader.list_available_engines(engine_dir):
            cats = engine_loader.peek_engine_categories(name, engine_dir)
            if any(c in cats for c in categories):
                engine_names.append(name)
    else:
        # Default: use all loaded engines, or load from dir
        if not engine_loader.engines:
            engine_loader.load_engines(engine_dir=engine_dir)
        engine_names = list(engine_loader.engines.keys())

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
        eng_fallback = getattr(eng, 'fallback_to_browser', False)
        eng_cdp_endpoint = getattr(eng, 'cdp_endpoint', "http://localhost:9222")
        eng_auto_launch = getattr(eng, 'auto_launch_browser', False)
        eng_headless = getattr(eng, 'headless', True)
        eng_browser_args = getattr(eng, 'browser_args', None)
        eng_block_resources = getattr(eng, 'block_resources', True)
        # Per-engine adapter backend: "" means use global default
        eng_adapter = getattr(eng, 'http_client', "") or None
        params = _build_default_params(
            query=query,
            pageno=pageno,
            language=language,
            time_range=time_range,
            safesearch=safesearch,
            timeout=min(timeout, getattr(eng, 'timeout', 10.0)),
            proxy=eng_proxy,
        )
        engine_params.append((eng, params, eng_fallback, eng_cdp_endpoint,
                              eng_auto_launch, eng_headless, eng_browser_args,
                              eng_block_resources, eng_adapter))

    # Execute engines concurrently via threads
    async def _run_in_thread(eng, params, fallback, cdp_endpoint,
                             auto_launch, headless, browser_args, block_res, adapter):
        return await asyncio.to_thread(
            _run_engine, eng, params, fallback, cdp_endpoint,
            auto_launch, headless, browser_args, block_res, adapter,
        )

    tasks = [
        _run_in_thread(eng, params, fb, cdp, al, hl, ba, br, ab)
        for eng, params, fb, cdp, al, hl, ba, br, ab in engine_params
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
    ))
