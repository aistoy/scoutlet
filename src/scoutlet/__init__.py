"""scoutlet - Minimal local search aggregator.

A lightweight search aggregation tool that reuses SearXNG's engine architecture
and result aggregation algorithm. Only API/CLI, no web UI.

Usage:
    from scoutlet import search_sync

    response = search_sync("python tutorial", engines=["brave", "qwant"])
    for r in response.results:
        print(f"[{','.join(r.engines)}] {r.title} - {r.url}")

    # Inspect per-engine outcome (what failed, what was skipped)
    for e in response.failed:
        print(f"  {e.name}: {e.status.value} - {e.error}")

    # With proxy
    response = search_sync("test", engines=["google"], proxy="socks5://127.0.0.1:1080")
"""

from scoutlet.result_types import SearchResult
from scoutlet.response import SearchResponse
from scoutlet.pipeline import search, search_sync
from scoutlet.engine_loader import (
    load_engine,
    load_engines,
    list_available_engines,
    engines as _engines,
)

__version__ = "0.2.0"
__all__ = [
    "search",
    "search_sync",
    "SearchResult",
    "SearchResponse",
    "load_engine",
    "load_engines",
    "list_available_engines",
]
