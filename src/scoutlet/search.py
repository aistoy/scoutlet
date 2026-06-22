"""Search pipeline for scoutlet.

Orchestrates: build params → concurrent engine execution → aggregate results.
"""

from __future__ import annotations

import asyncio
import re
import time
import typing as t

import httpx

from scoutlet import engine_loader
from scoutlet.result_types import SearchResult
from scoutlet.result_aggregation import ResultContainer
from scoutlet.outcome import EngineOutcome, FailureKind, classify_failure
from scoutlet.response import SearchResponse
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
) -> EngineOutcome:
    """Run a single engine search synchronously.

    Follows SearXNG's pattern:
    1. Call engine.request(query, params) → engine fills URL/headers
    2. Send HTTP request
    3. Call engine.response(resp) → engine parses and returns results

    Per-engine failures are caught, classified into FailureKind, and returned
    inside EngineOutcome. One broken engine doesn't abort the whole search.
    """
    engine_name = engine.name
    start = time.monotonic()

    def _elapsed_ms() -> int:
        return int((time.monotonic() - start) * 1000)

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

    phase = "request"
    try:
        # Step 1: Engine builds request params
        result = engine.request(params.get("query", ""), params)
        if result is not None:
            params = result

        if not params.get("url"):
            return EngineOutcome(
                engine=engine_name,
                status=FailureKind.EMPTY,
                elapsed_ms=_elapsed_ms(),
                error="engine.request() did not build a URL",
            )

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

        phase = "fetch"
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
        phase = "response"
        results = _parse_response(resp, params)

        if not results:
            return EngineOutcome(
                engine=engine_name,
                status=FailureKind.EMPTY,
                elapsed_ms=_elapsed_ms(),
            )

        return EngineOutcome(
            engine=engine_name,
            status=FailureKind.SUCCESS,
            elapsed_ms=_elapsed_ms(),
            results=results,
        )

    except Exception as e:
        status = classify_failure(e, phase)
        log.warning("Engine '%s' failed (%s, phase=%s): %s",
                    engine_name, status.value, phase, e)
        return EngineOutcome(
            engine=engine_name,
            status=status,
            elapsed_ms=_elapsed_ms(),
            error=str(e),
        )


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
) -> SearchResponse:
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
        SearchResponse with .results (list[SearchResult]), .engines
        (per-engine run info, including failures), and .skipped (engines
        filtered out before dispatch, e.g. in cooldown).
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

    # Get loaded engine modules, skipping engines currently in cooldown.
    # (Health registry is in-process; a fresh process starts with no
    # cooldowns, so first search is unaffected.)
    from scoutlet.health import get_default_registry
    from scoutlet.routing import plan_waves, coverage_satisfied
    from scoutlet.response import EngineRunInfo, SearchResponse, SkippedEngine
    health = get_default_registry()
    active_engines: list[t.Any] = []
    skipped: list[SkippedEngine] = []
    for name in engine_names:
        eng = engine_loader.engines.get(name)
        if eng is None:
            skipped.append(SkippedEngine(name=name, reason="not_loaded"))
            continue
        if not health.is_available(name):
            log.info("Engine '%s' skipped (in cooldown)", name)
            skipped.append(SkippedEngine(name=name, reason="cooldown"))
            continue
        active_engines.append(eng)

    if not active_engines:
        log.warning("No engines available for search")
        return SearchResponse(results=[], engines=[], skipped=skipped)

    # Two-wave routing. Explicit `engines=[...]` bypasses waves — the
    # caller asked for these specific engines, we run them all. Default
    # and category-based selection go through wave planning: general-
    # category engines cap at GENERAL_FIRST_WAVE (overlap is high),
    # vertical engines all run in wave one (unique coverage).
    first_wave, second_wave = plan_waves(active_engines, health, explicit=engines is not None)
    log.debug(
        "waves: first=%d (%s), second=%d (%s)",
        len(first_wave), [e.name for e in first_wave],
        len(second_wave), [e.name for e in second_wave],
    )

    # Time budget: keep total worst-case close to the caller's `timeout`.
    # Wave 1 gets 60%, wave 2 gets the remaining 40% (only spent if wave 2
    # actually fires). If waves are bypassed (explicit), full timeout.
    if second_wave:
        first_timeout = timeout * 0.6
        second_timeout = max(timeout * 0.4, 1.0)
    else:
        first_timeout = timeout
        second_timeout = 0.0

    def _build_engine_params(eng_list, per_timeout: float) -> list[tuple[t.Any, dict[str, t.Any], str | None]]:
        out = []
        for eng in eng_list:
            eng_proxy = getattr(eng, 'proxies', None) or proxy
            eng_adapter = getattr(eng, 'http_client', "") or search_adapter_backend
            params = _build_default_params(
                query=query,
                pageno=pageno,
                language=language,
                time_range=time_range,
                safesearch=safesearch,
                timeout=min(per_timeout, getattr(eng, 'timeout', 10.0)),
                proxy=eng_proxy,
            )
            out.append((eng, params, eng_adapter))
        return out

    async def _run_in_thread(eng, params, adapter):
        return await asyncio.to_thread(_run_engine, eng, params, adapter)

    async def _run_wave(engine_params_list):
        tasks = [
            _run_in_thread(eng, params, adapter)
            for eng, params, adapter in engine_params_list
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def _process_outcomes(engine_params_list, outcomes_list):
        """Update health + return clean list of EngineOutcome (no exceptions)."""
        clean = []
        for (eng, *_), outcome in zip(engine_params_list, outcomes_list):
            if isinstance(outcome, Exception):
                log.warning("Engine '%s' thread raised: %s", eng.name, outcome)
                continue
            health.update(outcome)
            clean.append(outcome)
        return clean

    def _feed_container(container, outcomes):
        for o in outcomes:
            if o.results:
                container.extend(o.engine, o.results)

    def _build_response(final_results: list[SearchResult], all_outcomes: list[t.Any]) -> SearchResponse:
        engine_runs = [
            EngineRunInfo(
                name=o.engine,
                status=o.status,
                elapsed_ms=o.elapsed_ms,
                error=o.error,
            )
            for o in all_outcomes
        ]
        return SearchResponse(
            results=final_results,
            engines=engine_runs,
            skipped=skipped,
        )

    # --- Wave 1 ---
    first_params = _build_engine_params(first_wave, first_timeout)
    first_outcomes_raw = await _run_wave(first_params)
    first_outcomes = _process_outcomes(first_params, first_outcomes_raw)

    container = ResultContainer(
        engines_registry=engine_loader.engines,
        health_registry=health,
    )
    _feed_container(container, first_outcomes)
    container.close()

    # Fast paths: no wave 2 to run, or wave 1 already covered it.
    if not second_wave:
        return _build_response(container.get_ordered_results(), first_outcomes)

    result_count = len(container._results_map)
    unique_domains = {
        (r.parsed_url.netloc if r.parsed_url else "")
        for r in container._results_map.values()
    }
    unique_engines = {
        eng for r in container._results_map.values() for eng in r.engines
    }

    if coverage_satisfied(result_count, len(unique_domains), len(unique_engines)):
        return _build_response(container.get_ordered_results(), first_outcomes)

    log.info(
        "Wave 1 coverage insufficient (results=%d, domains=%d, engines=%d); "
        "launching wave 2",
        result_count, len(unique_domains), len(unique_engines),
    )

    # --- Wave 2 ---
    second_params = _build_engine_params(second_wave, second_timeout)
    second_outcomes_raw = await _run_wave(second_params)
    second_outcomes = _process_outcomes(second_params, second_outcomes_raw)

    combined = ResultContainer(
        engines_registry=engine_loader.engines,
        health_registry=health,
    )
    _feed_container(combined, first_outcomes)
    _feed_container(combined, second_outcomes)
    combined.close()
    return _build_response(combined.get_ordered_results(), first_outcomes + second_outcomes)


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
) -> SearchResponse:
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
