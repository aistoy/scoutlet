"""Result aggregation for scoutlet, ported from SearXNG's results.py.

Implements:
- Score calculation (weighted by engine weight and position)
- Hash-based deduplication
- Result merging (keep longer text, merge engines, prefer HTTPS)
- Category-grouped sorting
"""

from __future__ import annotations

import typing as t
from threading import RLock

from scoutlet.result_types import SearchResult

import logging

log = logging.getLogger("scoutlet.aggregation")


def calculate_score(result: SearchResult, engines_registry: dict[str, t.Any]) -> float:
    """Calculate score for a result based on SearXNG's scoring formula.

    score = weight * sum(1/position) for each position
    weight = product(engine_weights) * len(positions)
    """
    weight = 1.0

    for engine_name in result.engines:
        engine = engines_registry.get(engine_name)
        if engine and hasattr(engine, 'weight'):
            weight *= float(engine.weight)

    weight *= len(result.positions)
    score = 0.0

    priority = result.priority

    for position in result.positions:
        if priority == 'low':
            continue
        if priority == 'high':
            score += weight
        else:  # normal or empty
            score += weight / position

    return score


def merge_two_results(origin: SearchResult, other: SearchResult) -> None:
    """Merge other result into origin, keeping the best content."""
    # Use content with more text
    if len(other.content or "") > len(origin.content or ""):
        origin.content = other.content

    # Use title with more text
    if len(other.title or "") > len(origin.title or ""):
        origin.title = other.title

    # Fill missing fields from other
    origin.defaults_from(other)

    # Merge engine sets
    origin.engines |= other.engines

    # Prefer HTTPS
    if origin.parsed_url and not origin.parsed_url.scheme.endswith("s"):
        if other.parsed_url and other.parsed_url.scheme.endswith("s"):
            origin.parsed_url = origin.parsed_url._replace(scheme=other.parsed_url.scheme)
            origin.url = origin.parsed_url.geturl()


class ResultContainer:
    """Collects, deduplicates, merges, scores and sorts search results.

    Ported from SearXNG's ResultContainer with simplified logic.
    """

    def __init__(self, engines_registry: dict[str, t.Any] | None = None):
        self._results_map: dict[int, SearchResult] = {}
        self._lock = RLock()
        self._closed = False
        self._sorted: list[SearchResult] | None = None
        self.engines_registry = engines_registry or {}

    def extend(self, engine_name: str, results: list[SearchResult]) -> None:
        """Add results from an engine."""
        if self._closed:
            return

        position = 0
        for result in results:
            if isinstance(result, dict):
                # Convert dict to SearchResult
                result = SearchResult(**{k: v for k, v in result.items()
                                         if k in SearchResult.__dataclass_fields__})

            result.engine = result.engine or engine_name
            result.normalize()

            position += 1
            self._merge_result(result, position)

    def _merge_result(self, result: SearchResult, position: int) -> None:
        """Merge result with existing results or add as new."""
        try:
            result_hash = hash(result)
        except ValueError:
            # Result without parsed_url, just append
            result.positions = [position]
            result_hash = id(result)
            self._results_map[result_hash] = result
            return

        with self._lock:
            existing = self._results_map.get(result_hash)
            if not existing:
                result.positions = [position]
                self._results_map[result_hash] = result
                return

            merge_two_results(existing, result)
            existing.positions.append(position)

    def close(self) -> None:
        """Close container and calculate scores."""
        self._closed = True
        for result in self._results_map.values():
            result.score = calculate_score(result, self.engines_registry)

    def get_ordered_results(self) -> list[SearchResult]:
        """Return sorted, deduplicated results.

        Two-pass sort:
        1. By score (descending)
        2. Category grouping (max 8 per group, max distance 20)
        """
        if not self._closed:
            self.close()

        if self._sorted is not None:
            return self._sorted

        # Pass 1: sort by score descending
        results = sorted(self._results_map.values(), key=lambda x: x.score, reverse=True)

        # Pass 2: group by category and template
        gresults: list[SearchResult] = []
        category_positions: dict[str, dict[str, t.Any]] = {}
        max_count = 8
        max_distance = 20

        for res in results:
            # Determine category
            engine = self.engines_registry.get(res.engine or "")
            if engine and hasattr(engine, 'categories') and engine.categories:
                res.category = engine.categories[0]
            elif not res.category:
                res.category = "general"

            category = f"{res.category}:{res.template}:{'img' if (res.thumbnail or res.img_src) else ''}"
            grp = category_positions.get(category)

            if (grp is not None) and (grp["count"] > 0) and (len(gresults) - grp["index"] < max_distance):
                index = grp["index"]
                gresults.insert(index, res)
                # Update indexes after insertion
                for item in category_positions.values():
                    if item["index"] >= index:
                        item["index"] += 1
                grp["count"] -= 1
            else:
                gresults.append(res)
                category_positions[category] = {"index": len(gresults), "count": max_count}

        self._sorted = gresults
        return self._sorted
