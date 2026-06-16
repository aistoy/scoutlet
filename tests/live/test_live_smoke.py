"""Live smoke tests for P0 engines.

These tests require network access and are gated behind SCOUTLET_LIVE=1.
CI should not run these by default.

Usage:
    SCOUTLET_LIVE=1 uv run pytest tests/live/ -v
"""

import os

import pytest

from scoutlet.search import search_sync

# P0 engines to smoke test
P0_ENGINES = ["bing", "google", "duckduckgo", "qwant", "baidu"]

# Skip entire module if SCOUTLET_LIVE is not set
pytestmark = pytest.mark.skipif(
    os.environ.get("SCOUTLET_LIVE") != "1",
    reason="Live tests disabled. Set SCOUTLET_LIVE=1 to enable.",
)


@pytest.mark.live
@pytest.mark.timeout(30)
@pytest.mark.parametrize("engine", P0_ENGINES)
def test_engine_returns_results(engine: str):
    """Each P0 engine should return at least 1 result for a basic query."""
    results = search_sync("python tutorial", engines=[engine])
    assert len(results) >= 1, f"{engine} returned 0 results"
    for r in results:
        assert r.url, f"{engine} result missing url"
        assert r.title, f"{engine} result missing title"


@pytest.mark.live
@pytest.mark.timeout(30)
def test_multi_engine_aggregation():
    """Multi-engine search should aggregate and deduplicate."""
    results = search_sync("python tutorial", engines=["bing", "brave"])
    assert len(results) >= 2
    # All results should have score > 0
    assert all(r.score > 0 for r in results)
