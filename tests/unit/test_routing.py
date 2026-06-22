"""Unit tests for two-wave engine routing."""

import types

import pytest

from scoutlet.health import EngineHealthRegistry
from scoutlet.routing import (
    GENERAL_FIRST_WAVE,
    GENERAL_SECOND_WAVE,
    MIN_RESULTS,
    MIN_UNIQUE_DOMAINS,
    MIN_UNIQUE_ENGINES,
    _priority,
    coverage_satisfied,
    plan_waves,
)


def _make_engine(name: str, weight: float = 1.0, categories: list[str] | None = None):
    eng = types.ModuleType(name)
    eng.name = name
    eng.weight = weight
    eng.categories = categories or ["general"]
    return eng


class TestPlanWaves:
    def test_explicit_engines_bypass_waves(self):
        """Caller-provided engines all go in wave one."""
        engines = [_make_engine(f"g{i}") for i in range(8)]
        reg = EngineHealthRegistry()
        first, second = plan_waves(engines, reg, explicit=True)
        assert len(first) == 8
        assert second == []

    def test_general_engines_capped_at_first_wave(self):
        engines = [_make_engine(f"g{i}", weight=1.0) for i in range(7)]
        reg = EngineHealthRegistry()
        first, second = plan_waves(engines, reg, explicit=False)
        assert len(first) == GENERAL_FIRST_WAVE
        assert len(second) == GENERAL_SECOND_WAVE  # 7 - 4 = 3

    def test_vertical_engines_all_in_wave_one(self):
        engines = [_make_engine(f"v{i}", categories=["images"]) for i in range(10)]
        reg = EngineHealthRegistry()
        first, second = plan_waves(engines, reg, explicit=False)
        assert len(first) == 10
        assert second == []

    def test_mixed_general_and_vertical(self):
        # 6 general + 4 vertical
        engines = (
            [_make_engine(f"g{i}") for i in range(6)]
            + [_make_engine(f"v{i}", categories=["images"]) for i in range(4)]
        )
        reg = EngineHealthRegistry()
        first, second = plan_waves(engines, reg, explicit=False)
        # First wave: 4 general + 4 vertical = 8
        assert len(first) == 8
        # Second wave: 2 leftover general
        assert len(second) == 2
        assert all(getattr(e, "categories") != ["general"] or "general" in e.categories for e in second)

    def test_general_engines_under_cap_all_in_first_wave(self):
        engines = [_make_engine(f"g{i}") for i in range(3)]
        reg = EngineHealthRegistry()
        first, second = plan_waves(engines, reg, explicit=False)
        assert len(first) == 3
        assert second == []

    def test_higher_weight_general_engine_ranks_into_first_wave(self):
        engines = [
            _make_engine("g_low", weight=0.5),
            _make_engine("g_high", weight=5.0),
            _make_engine("g_mid", weight=1.0),
            _make_engine("g_low2", weight=0.5),
            _make_engine("g_low3", weight=0.5),  # this one should overflow
        ]
        reg = EngineHealthRegistry()
        first, second = plan_waves(engines, reg, explicit=False)
        first_names = {e.name for e in first}
        assert "g_high" in first_names
        assert "g_low3" not in first_names
        assert {e.name for e in second} == {"g_low3"}

    def test_slow_engine_demoted(self):
        """An engine with bad latency EMA ranks lower than a fast one."""
        reg = EngineHealthRegistry()
        # Manually seed latency: slow=2000ms, fast=50ms
        reg.get("slow").latency_ema_ms = 2000.0
        reg.get("fast").latency_ema_ms = 50.0
        engines = [
            _make_engine("slow", weight=1.0),
            _make_engine("fast", weight=1.0),
            _make_engine("mid1", weight=1.0),
            _make_engine("mid2", weight=1.0),
            _make_engine("slow2", weight=1.0),  # expected overflow
        ]
        first, second = plan_waves(engines, reg, explicit=False)
        # "slow" should be demoted into second wave if mid* engines are faster
        # All start with ema=0 except slow/fast; mid1/mid2 default to 50ms clamp
        # Priority: fast (1000/50=20) > mid1=mid2=slow2 (1000/50=20) > slow (1000/2000=0.5)
        second_names = {e.name for e in second}
        assert "slow" in second_names


class TestCoverageSatisfied:
    def test_all_thresholds_met(self):
        assert coverage_satisfied(
            result_count=15,
            unique_domains=8,
            unique_engines=3,
        ) is True

    def test_below_min_results(self):
        assert coverage_satisfied(5, 10, 3) is False

    def test_below_min_domains(self):
        assert coverage_satisfied(20, 3, 3) is False

    def test_below_min_engines(self):
        assert coverage_satisfied(20, 10, 1) is False

    def test_exact_thresholds_pass(self):
        assert coverage_satisfied(MIN_RESULTS, MIN_UNIQUE_DOMAINS, MIN_UNIQUE_ENGINES) is True

    def test_below_threshold_in_one_dimension_fails(self):
        """Any single dimension failing returns False (AND semantics)."""
        assert coverage_satisfied(MIN_RESULTS - 1, MIN_UNIQUE_DOMAINS, MIN_UNIQUE_ENGINES) is False
        assert coverage_satisfied(MIN_RESULTS, MIN_UNIQUE_DOMAINS - 1, MIN_UNIQUE_ENGINES) is False
        assert coverage_satisfied(MIN_RESULTS, MIN_UNIQUE_DOMAINS, MIN_UNIQUE_ENGINES - 1) is False


class TestPriority:
    def test_fresh_engine_has_moderate_priority(self):
        """Engines with no history get success_rate=0.5 — neither top nor bottom."""
        eng = _make_engine("fresh", weight=1.0)
        reg = EngineHealthRegistry()
        p = _priority(eng, reg)
        # weight(1) * sr(0.5) * latency(1000/50=20) = 10.0
        assert p == pytest.approx(10.0)

    def test_high_weight_boosts_priority(self):
        eng_low = _make_engine("low", weight=1.0)
        eng_high = _make_engine("high", weight=10.0)
        reg = EngineHealthRegistry()
        assert _priority(eng_high, reg) > _priority(eng_low, reg)

    def test_low_success_rate_demotes(self):
        eng = _make_engine("flaky", weight=1.0)
        reg = EngineHealthRegistry()
        h = reg.get("flaky")
        h.success_count = 1
        h.failure_count = 9  # success_rate = 0.1
        p_flaky = _priority(eng, reg)
        h2 = reg.get("healthy")
        h2.success_count = 9
        h2.failure_count = 1  # success_rate = 0.9
        eng_h = _make_engine("healthy", weight=1.0)
        p_healthy = _priority(eng_h, reg)
        assert p_healthy > p_flaky
