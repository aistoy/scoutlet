"""In-process engine health registry.

Tracks per-engine success/failure history and cooldown state so the
search orchestrator can skip engines that are currently dead (CAPTCHA'd,
rate-limited, or in a failure streak).

State is process-wide and not persisted. A fresh process starts with
empty health for every engine; cooldowns clear on restart. This is
intentional — for an embeddable library used inside agent scripts and
CLIs, cross-session persistence introduces schema/lock/staleness issues
whose benefit rarely justifies the cost.

Thread safety: update() is called from asyncio.to_thread workers, so
the registry takes a lock around mutations.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from scoutlet.outcome import EngineOutcome, FailureKind


# Cooldown rules (seconds).
# Triggered by update() based on the outcome's status / streak.
ANTIBOT_COOLDOWN_SEC = 300        # CAPTCHA / AccessDenied / block page
RATE_LIMIT_COOLDOWN_SEC = 300     # 429
FAILURE_STREAK_THRESHOLD = 3      # consecutive failures triggering streak cooldown
FAILURE_STREAK_COOLDOWN_SEC = 600
SUCCESS_RATE_BAD = 0.3            # below this → result scoring penalizes the engine


@dataclass
class EngineHealth:
    success_count: int = 0
    failure_count: int = 0
    empty_count: int = 0
    anti_bot_count: int = 0
    rate_limit_count: int = 0
    timeout_count: int = 0
    latency_ema_ms: float = 0.0    # exponential moving average
    last_status: FailureKind | None = None
    last_success_at: float | None = None
    cooldown_until: float = 0.0    # epoch seconds; 0 means no cooldown
    consecutive_failures: int = 0

    @property
    def total(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        t = self.total
        return self.success_count / t if t else 0.0

    @property
    def in_cooldown(self) -> bool:
        return self.cooldown_until > time.time()

    @property
    def is_bad(self) -> bool:
        """True when scoring should penalize this engine."""
        if self.in_cooldown:
            return True
        return self.total >= 5 and self.success_rate < SUCCESS_RATE_BAD


_LATENCY_EMA_ALPHA = 0.3  # weight given to the newest sample


class EngineHealthRegistry:
    """Thread-safe map of {engine_name: EngineHealth}."""

    def __init__(self) -> None:
        self._health: dict[str, EngineHealth] = {}
        self._lock = threading.Lock()

    def get(self, name: str) -> EngineHealth:
        """Return health for an engine, creating an empty record on first access."""
        with self._lock:
            h = self._health.get(name)
            if h is None:
                h = EngineHealth()
                self._health[name] = h
            return h

    def is_available(self, name: str) -> bool:
        """False when the engine is currently in cooldown."""
        return not self.get(name).in_cooldown

    def update(self, outcome: EngineOutcome) -> None:
        """Fold an engine outcome into the registry, applying cooldown rules."""
        now = time.time()
        h = self.get(outcome.engine)
        with self._lock:
            # Latency EMA: include all outcomes (failures still reveal latency)
            if outcome.elapsed_ms > 0:
                h.latency_ema_ms = (
                    _LATENCY_EMA_ALPHA * outcome.elapsed_ms
                    + (1 - _LATENCY_EMA_ALPHA) * h.latency_ema_ms
                )
            h.last_status = outcome.status

            if outcome.status == FailureKind.SUCCESS:
                h.success_count += 1
                h.last_success_at = now
                h.consecutive_failures = 0
                h.cooldown_until = 0.0
                return

            # Failure accounting
            h.failure_count += 1
            h.consecutive_failures += 1

            if outcome.status == FailureKind.EMPTY:
                h.empty_count += 1
            elif outcome.status == FailureKind.ANTI_BOT:
                h.anti_bot_count += 1
                h.cooldown_until = max(h.cooldown_until, now + ANTIBOT_COOLDOWN_SEC)
            elif outcome.status == FailureKind.RATE_LIMIT:
                h.rate_limit_count += 1
                h.cooldown_until = max(h.cooldown_until, now + RATE_LIMIT_COOLDOWN_SEC)
            elif outcome.status == FailureKind.TIMEOUT:
                h.timeout_count += 1

            # Streak cooldown on top of status-specific cooldown
            if h.consecutive_failures >= FAILURE_STREAK_THRESHOLD:
                h.cooldown_until = max(h.cooldown_until, now + FAILURE_STREAK_COOLDOWN_SEC)

    def snapshot(self) -> dict[str, dict]:
        """Point-in-time view of every engine's health. For diagnostics."""
        with self._lock:
            out = {}
            for name, h in self._health.items():
                out[name] = {
                    "success": h.success_count,
                    "failure": h.failure_count,
                    "empty": h.empty_count,
                    "anti_bot": h.anti_bot_count,
                    "rate_limit": h.rate_limit_count,
                    "timeout": h.timeout_count,
                    "latency_ema_ms": round(h.latency_ema_ms, 1),
                    "success_rate": round(h.success_rate, 3),
                    "last_status": h.last_status.value if h.last_status else None,
                    "in_cooldown": h.in_cooldown,
                    "cooldown_until": h.cooldown_until or None,
                    "is_bad": h.is_bad,
                }
            return out

    def reset(self) -> None:
        """Clear all health state. Intended for tests."""
        with self._lock:
            self._health.clear()


# Module-level default registry. Tests should call reset() between cases
# to avoid cross-test contamination.
_default_registry: EngineHealthRegistry | None = None


def get_default_registry() -> EngineHealthRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = EngineHealthRegistry()
    return _default_registry


def reset_default_registry() -> None:
    """Reset the module-level registry. For tests and CLI freshness."""
    global _default_registry
    if _default_registry is not None:
        _default_registry.reset()
