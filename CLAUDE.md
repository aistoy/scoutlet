# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

scoutlet is a lightweight Python search aggregation library that reuses SearXNG's engine architecture and result aggregation algorithm. It runs as a library or CLI — no web service, no Docker, no API keys. Positioned as a "SearXNG-lite" embeddable core for AI agents and scripts.

## Development Commands

```bash
# Install (editable)
uv sync
uv sync --extra dev        # with pytest, respx, pytest-timeout
uv sync --extra fingerprint # with primp for TLS impersonation

# Run tests
uv run pytest tests/                          # all tests (offline)
uv run pytest tests/unit/                      # unit tests only
uv run pytest tests/engines/                   # engine parser fixture tests
uv run pytest tests/unit/test_result_types.py  # single test file
uv run pytest -k "test_hash"                   # single test by name

# CLI
scoutlet "python tutorial" -e google,bing -f json
scoutlet --list-engines
```

Live tests (require network) are gated behind `pytest.mark.live` and excluded by default.

## Architecture

### Search Pipeline

```
search() / search_sync()
  → engine_loader.load_engines()       # discover & register engine modules
  → _build_default_params()            # per-engine params (headers, proxy, timeout)
  → _run_engine() per engine           # in thread pool
      → engine.request(query, params)  # engine fills URL/headers
      → network.get/post()             # HTTP request
      → engine.response(resp)          # engine parses HTML/JSON → list[dict]
  → ResultContainer.extend()           # dedup, merge, score
  → ResultContainer.get_ordered_results()
```

### Core Modules (src/scoutlet/)

- **`search.py`** — Orchestrator. `search()` is async, `search_sync()` wraps it via `asyncio.run()`. Engines run concurrently via `asyncio.to_thread`.
- **`result_types.py`** — `SearchResult` dataclass with SearXNG-compatible hash-based dedup. `EngineResults` is a typed list.
- **`result_aggregation.py`** — `ResultContainer` implements SearXNG scoring: `weight × Σ(1/position)`, plus merge (longer content wins, HTTPS preferred) and category-grouped sorting.
- **`engine_loader.py`** — Three-tier loading: external dir (`~/.scoutlet/engines/`) overrides bundled (`src/scoutlet/engines/`). Engines are Python modules with `request()`/`response()` functions.
- **`network.py`** — Thin httpx wrapper. `raise_for_httperror()` maps 403/503→AccessDenied, 429→TooManyRequests, other 4xx/5xx→APIException.
- **`response_classifier.py`** — Pure-HTTP block-page detector. `detect_block_page()` checks engine-specific patterns (Google sorry, Bing block) and generic anti-bot keywords (Cloudflare, Akamai, PerimeterX). No browser dependency.
- **`traits.py`** — Engine language/region support loaded from `data/engine_traits.json`.
- **`utils.py`** — XPath helpers, text extraction, user-agent generation, URL normalization. Ported from SearXNG.

### Engine Pattern

Each engine in `src/scoutlet/engines/` is a Python module with:
- Module-level config: `categories`, `paging`, `time_range_support`, `safesearch`, `weight`
- `request(query, params) -> params | None` — fills URL, headers, cookies
- `response(resp) -> list[dict]` — parses HTML (via lxml xpath) or JSON into result dicts

Engines are adapted from SearXNG: change `from searx.*` → `from scoutlet.*`, remove fetch_traits (loaded from JSON instead).

### Key Design Decisions

- `search()` returns `list[SearchResult]`, not raw dicts — the container normalizes, deduplicates, and scores before returning.
- Hash-based dedup uses `template|netloc|path|params|query|fragment|img_src` — same URL from multiple engines gets merged (corroboration boosts score).
- Per-engine HTTP failures are caught and logged; one broken engine doesn't abort the whole search.
- SOCKS5 proxy requires `httpx[socks]` extra — not installed by default.
- Optional `primp` adapter (`fingerprint` extra) provides TLS-layer impersonation; no headless-browser fallback shipped in main.

## Test Structure

```
tests/
  unit/           # Core logic tests (offline, no network)
  engines/        # Engine parser fixture tests (offline, uses saved HTML/JSON)
  fixtures/       # Minimal HTML/JSON fixtures per engine
  live/           # Network-dependent tests (gated by pytest.mark.live)
```

When adding a new engine or modifying a parser, create a minimal fixture in `tests/fixtures/engines/<name>/` and add parser tests in `tests/engines/test_<name>_parser.py`.
