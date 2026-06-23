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

import enum
from dataclasses import dataclass, field
from typing import Any

from scoutlet.outcome import EngineOutcome, FailureKind
from scoutlet.result_types import SearchResult


class SearchStatus(enum.Enum):
    """Top-level outcome of a search call.

    Replaces a boolean ``partial`` field: ``partial=false`` on total
    failure was too easy to read as "everything is fine".
    """
    SUCCESS = "success"   # every executed engine returned SUCCESS (incl. EMPTY)
    PARTIAL = "partial"   # at least one engine succeeded AND at least one failed/was skipped
    FAILED = "failed"     # no engine succeeded


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


def compute_status(
    outcomes: list[EngineOutcome],
    skipped: list[SkippedEngine],
) -> SearchStatus:
    """Derive top-level status from per-engine outcomes + skipped list.

    EMPTY counts as success-equivalent (§6.2 B: a normal empty result is
    a valid outcome, not a failure).

    - No engines ran and nothing skipped → SUCCESS (vacuous call).
    - All executed engines returned SUCCESS-or-EMPTY and nothing skipped → SUCCESS.
    - At least one success-equivalent AND at least one real failure or skip → PARTIAL.
    - No success-equivalent at all → FAILED.
    """
    if not outcomes and not skipped:
        return SearchStatus.SUCCESS

    success_like = (FailureKind.SUCCESS, FailureKind.EMPTY)
    any_success = any(o.status in success_like for o in outcomes)
    any_non_success = any(o.status not in success_like for o in outcomes)

    if any_success and (any_non_success or skipped):
        return SearchStatus.PARTIAL
    if any_success:
        return SearchStatus.SUCCESS
    return SearchStatus.FAILED


def collect_snippet_warnings(results: list[SearchResult]) -> list[str]:
    """Scan results for missing snippets; return agent-facing warnings.

    A None snippet (§6.2 D) means the engine didn't supply usable text
    for that candidate. Agents that gate fetch decisions on snippet need
    to know how many candidates are flying blind so they can choose to
    fetch anyway or reformulate. We summarize as a count rather than
    per-result messages to keep the warnings list readable.
    """
    if not results:
        return []
    missing = sum(1 for r in results if r.snippet is None)
    if missing == 0:
        return []
    return [f"{missing}/{len(results)} results have no snippet (agent must fetch to assess)"]


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
    query: str = ""
    status: SearchStatus = SearchStatus.SUCCESS
    warnings: list[str] = field(default_factory=list)

    @property
    def failed(self) -> list[EngineRunInfo]:
        """Engines that ran but did not return SUCCESS."""
        return [e for e in self.engines if e.status != FailureKind.SUCCESS]

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "status": self.status.value,
            "results": [r.as_dict() for r in self.results],
            "engines": [e.as_dict() for e in self.engines],
            "skipped": [s.as_dict() for s in self.skipped],
            "warnings": list(self.warnings),
        }
