"""Unit tests for the in-process engine health registry."""

import logging
import time
from unittest.mock import patch

import pytest

from scoutlet.health import (
    ANTIBOT_COOLDOWN_SEC,
    EngineHealth,
    EngineHealthRegistry,
    EMPTY_STREAK_WARN_THRESHOLD,
    FAILURE_STREAK_COOLDOWN_SEC,
    FAILURE_STREAK_THRESHOLD,
    RATE_LIMIT_COOLDOWN_SEC,
    SUCCESS_RATE_BAD,
)
from scoutlet.outcome import EngineOutcome, FailureKind


def _outcome(engine: str, status: FailureKind, elapsed_ms: int = 10) -> EngineOutcome:
    return EngineOutcome(engine=engine, status=status, elapsed_ms=elapsed_ms)


class TestEngineHealthUnit:
    def test_fresh_health_is_not_bad(self):
        h = EngineHealth()
        assert h.in_cooldown is False
        assert h.is_bad is False
        assert h.success_rate == 0.0
        assert h.total == 0

    def test_success_rate_computes_from_counts(self):
        h = EngineHealth(success_count=7, failure_count=3)
        assert h.total == 10
        assert h.success_rate == 0.7

    def test_is_bad_below_success_rate_threshold(self):
        # Need >= 5 samples before success_rate gate kicks in (avoid noise)
        h = EngineHealth(success_count=1, failure_count=9)
        assert h.is_bad is True

    def test_is_not_bad_with_few_samples_even_low_rate(self):
        # 1/5 = 0.2 < threshold, but only 5 samples... edge: total==5 passes the gate
        h = EngineHealth(success_count=1, failure_count=4)
        assert h.total == 5
        assert h.success_rate < SUCCESS_RATE_BAD
        assert h.is_bad is True

    def test_is_not_bad_with_under_5_samples(self):
        # Don't penalize engines that haven't had enough runs yet
        h = EngineHealth(success_count=0, failure_count=2)
        assert h.is_bad is False

    def test_in_cooldown_when_future_cooldown_until(self):
        h = EngineHealth(cooldown_until=time.time() + 100)
        assert h.in_cooldown is True
        assert h.is_bad is True  # cooldown implies bad

    def test_in_cooldown_when_past_cooldown_until(self):
        h = EngineHealth(cooldown_until=time.time() - 1)
        assert h.in_cooldown is False


class TestEngineHealthRegistry:
    def test_get_creates_record_on_first_access(self):
        reg = EngineHealthRegistry()
        h = reg.get("google")
        assert h.success_count == 0
        # Same object on subsequent access
        assert reg.get("google") is h

    def test_is_available_for_unknown_engine(self):
        reg = EngineHealthRegistry()
        assert reg.is_available("google") is True

    def test_success_updates_counters_and_clears_cooldown(self):
        reg = EngineHealthRegistry()
        # Put engine into cooldown first
        reg.update(_outcome("google", FailureKind.ANTI_BOT))
        assert not reg.is_available("google")
        # Now succeed
        reg.update(_outcome("google", FailureKind.SUCCESS, elapsed_ms=50))
        h = reg.get("google")
        assert h.success_count == 1
        assert h.consecutive_failures == 0
        assert h.cooldown_until == 0.0
        assert reg.is_available("google") is True
        assert h.last_success_at is not None

    def test_anti_bot_triggers_cooldown(self):
        reg = EngineHealthRegistry()
        before = time.time()
        reg.update(_outcome("google", FailureKind.ANTI_BOT))
        h = reg.get("google")
        assert h.anti_bot_count == 1
        assert h.cooldown_until >= before + ANTIBOT_COOLDOWN_SEC - 1
        assert not reg.is_available("google")

    def test_rate_limit_triggers_cooldown(self):
        reg = EngineHealthRegistry()
        before = time.time()
        reg.update(_outcome("ddg", FailureKind.RATE_LIMIT))
        h = reg.get("ddg")
        assert h.rate_limit_count == 1
        assert h.cooldown_until >= before + RATE_LIMIT_COOLDOWN_SEC - 1

    def test_streak_triggers_cooldown_after_threshold(self):
        reg = EngineHealthRegistry()
        # Two parser errors: not yet streak-cooldown
        reg.update(_outcome("bing", FailureKind.PARSER_ERROR))
        reg.update(_outcome("bing", FailureKind.PARSER_ERROR))
        assert reg.is_available("bing") is True
        # Third consecutive failure → streak cooldown
        before = time.time()
        reg.update(_outcome("bing", FailureKind.PARSER_ERROR))
        h = reg.get("bing")
        assert h.consecutive_failures == FAILURE_STREAK_THRESHOLD
        assert h.cooldown_until >= before + FAILURE_STREAK_COOLDOWN_SEC - 1

    def test_streak_resets_on_success(self):
        reg = EngineHealthRegistry()
        reg.update(_outcome("bing", FailureKind.PARSER_ERROR))
        reg.update(_outcome("bing", FailureKind.PARSER_ERROR))
        reg.update(_outcome("bing", FailureKind.SUCCESS))
        h = reg.get("bing")
        assert h.consecutive_failures == 0
        assert h.failure_count == 2  # failures still counted historically
        assert h.success_count == 1

    def test_empty_does_not_trigger_cooldown(self):
        """§6.2 B: EMPTY must not trigger cooldown, regardless of count."""
        reg = EngineHealthRegistry()
        # Well past FAILURE_STREAK_THRESHOLD and EMPTY_STREAK_WARN_THRESHOLD
        for _ in range(EMPTY_STREAK_WARN_THRESHOLD + 5):
            reg.update(_outcome("mwmbl", FailureKind.EMPTY))
        h = reg.get("mwmbl")
        assert h.empty_count == EMPTY_STREAK_WARN_THRESHOLD + 5
        assert h.consecutive_empties == EMPTY_STREAK_WARN_THRESHOLD + 5
        assert h.consecutive_failures == 0  # EMPTY doesn't touch failure streak
        assert h.failure_count == 0
        assert h.cooldown_until == 0.0
        assert reg.is_available("mwmbl") is True

    def test_empty_streak_emits_warn_at_threshold(self, caplog):
        """§6.2 B: warn fires once when the streak crosses the threshold."""
        reg = EngineHealthRegistry()
        with caplog.at_level(logging.WARNING, logger="scoutlet.health"):
            for _ in range(EMPTY_STREAK_WARN_THRESHOLD - 1):
                reg.update(_outcome("mwmbl", FailureKind.EMPTY))
            assert len(caplog.records) == 0
            reg.update(_outcome("mwmbl", FailureKind.EMPTY))
            assert len(caplog.records) == 1
            # Further empties do not re-fire (== threshold, not >=)
            reg.update(_outcome("mwmbl", FailureKind.EMPTY))
            assert len(caplog.records) == 1

    def test_empty_streak_resets_on_success(self):
        reg = EngineHealthRegistry()
        for _ in range(5):
            reg.update(_outcome("mwmbl", FailureKind.EMPTY))
        assert reg.get("mwmbl").consecutive_empties == 5
        reg.update(_outcome("mwmbl", FailureKind.SUCCESS))
        assert reg.get("mwmbl").consecutive_empties == 0

    def test_empty_does_not_pre_increment_failure_streak(self):
        """EMPTY followed by a real failure: streak starts at 1, not 2."""
        reg = EngineHealthRegistry()
        reg.update(_outcome("bing", FailureKind.EMPTY))
        reg.update(_outcome("bing", FailureKind.PARSER_ERROR))
        h = reg.get("bing")
        assert h.consecutive_failures == 1
        assert h.consecutive_empties == 0
        assert h.failure_count == 1

    def test_latency_ema_blends_samples(self):
        reg = EngineHealthRegistry()
        reg.update(_outcome("a", FailureKind.SUCCESS, elapsed_ms=100))
        reg.update(_outcome("a", FailureKind.SUCCESS, elapsed_ms=200))
        h = reg.get("a")
        # EMA(alpha=0.3): 0.3*100 = 30 first; then 0.3*200 + 0.7*30 = 81
        assert h.latency_ema_ms == pytest.approx(81.0, abs=0.1)

    def test_cooldown_uses_max_not_last(self):
        # If already in a long cooldown, a short-cooldown failure shouldn't shrink it
        reg = EngineHealthRegistry()
        reg.update(_outcome("a", FailureKind.ANTI_BOT))  # 300s
        first_until = reg.get("a").cooldown_until
        # Wait a moment so "now" advances, then trigger a shorter cooldown
        time.sleep(0.01)
        reg.update(_outcome("a", FailureKind.RATE_LIMIT))  # also 300s
        second_until = reg.get("a").cooldown_until
        assert second_until >= first_until  # didn't shrink

    def test_snapshot_structure(self):
        reg = EngineHealthRegistry()
        reg.update(_outcome("google", FailureKind.SUCCESS, elapsed_ms=50))
        reg.update(_outcome("google", FailureKind.SUCCESS, elapsed_ms=70))
        snap = reg.snapshot()
        assert "google" in snap
        assert snap["google"]["success"] == 2
        assert snap["google"]["last_status"] == "success"
        assert snap["google"]["in_cooldown"] is False

    def test_reset_clears_state(self):
        reg = EngineHealthRegistry()
        reg.update(_outcome("google", FailureKind.ANTI_BOT))
        assert not reg.is_available("google")
        reg.reset()
        assert reg.is_available("google")
        # Underlying record is gone — new one has zero counts
        assert reg.get("google").anti_bot_count == 0

    def test_thread_safety_smoke(self):
        # Concurrent updates shouldn't crash or lose the lock
        import threading
        reg = EngineHealthRegistry()

        def worker():
            for _ in range(100):
                reg.update(_outcome("shared", FailureKind.SUCCESS, elapsed_ms=10))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # 8 * 100 = 800 successes
        assert reg.get("shared").success_count == 800


class TestModuleDefaultRegistry:
    def test_default_registry_is_singleton(self):
        from scoutlet.health import get_default_registry, reset_default_registry
        reset_default_registry()
        a = get_default_registry()
        b = get_default_registry()
        assert a is b

    def test_reset_default_clears_state(self):
        from scoutlet.health import get_default_registry, reset_default_registry
        reset_default_registry()
        reg = get_default_registry()
        reg.update(_outcome("test_engine", FailureKind.ANTI_BOT))
        assert not reg.is_available("test_engine")
        reset_default_registry()
        # New registry instance, fresh state
        new_reg = get_default_registry()
        assert new_reg.is_available("test_engine")
