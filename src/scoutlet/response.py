"""Agent-facing search response.

Replaces the bare ``list[SearchResult]`` return of ``search()`` with a
structured response carrying per-engine outcomes and skipped engines,
so agents can reason about what happened (which engines failed, which
were filtered) without reading log output.

Minimal field set on purpose — wave mechanics, coverage scores, and
timing totals are intentionally omitted. Add them only when a concrete
agent use case demands it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scoutlet.outcome import FailureKind
from scoutlet.result_types import SearchResult


@dataclass
class EngineRunInfo:
    """What happened when a single engine ran."""
    name: str
    status: FailureKind
    elapsed_ms: int
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
        }


@dataclass
class SkippedEngine:
    """An engine that was selected but didn't run."""
    name: str
    reason: str               # "cooldown" / "not_loaded" / "load_failed"

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "reason": self.reason}


@dataclass
class SearchResponse:
    """What ``search()`` and ``search_sync()`` return.

    Agents that don't care about diagnostics can use ``response.results``
    exactly like the old list. Agents that want to adapt (retry with
    different engines, report failures) read ``engines`` and ``skipped``.
    """
    results: list[SearchResult] = field(default_factory=list)
    engines: list[EngineRunInfo] = field(default_factory=list)
    skipped: list[SkippedEngine] = field(default_factory=list)

    @property
    def failed(self) -> list[EngineRunInfo]:
        """Engines that ran but did not return SUCCESS."""
        return [e for e in self.engines if e.status != FailureKind.SUCCESS]

    def as_dict(self) -> dict[str, Any]:
        return {
            "results": [r.as_dict() for r in self.results],
            "engines": [e.as_dict() for e in self.engines],
            "skipped": [s.as_dict() for s in self.skipped],
        }
