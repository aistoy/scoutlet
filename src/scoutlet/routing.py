"""Two-wave engine routing.

Splits the candidate engine list into a first wave (run immediately) and
a second wave (run only if first-wave coverage is insufficient).

Rules agreed for scoutlet:

  - General-category engines overlap heavily (google/bing/baidu/sogou/
    duckduckgo mostly return the same top URLs), so running all of them
    is wasted latency. Cap the first wave at GENERAL_FIRST_WAVE (4).
  - Vertical-category engines (images, videos, code, music, ...) have
    unique coverage — skipping them loses real results. No cap; all go
    in the first wave.
  - Explicit ``engines=[...]`` from the caller is treated as intent,
    not a candidate pool. All engines run in the first wave; two-wave
    routing is bypassed entirely.
  - Engines in cooldown (per the health registry) are filtered out
    before wave assignment.
"""

from __future__ import annotations

import typing as t


GENERAL_FIRST_WAVE = 4
GENERAL_SECOND_WAVE = 3

# Coverage thresholds for deciding whether the first wave was "enough".
# Any one of these failing triggers the second wave.
MIN_RESULTS = 10
MIN_UNIQUE_DOMAINS = 5
MIN_UNIQUE_ENGINES = 2


def _priority(engine: t.Any, health: t.Any) -> float:
    """Sort key: higher = more likely to be in the first wave.

    Combines engine static weight, recent health, and typical latency.
    """
    import time
    weight = float(getattr(engine, "weight", 1.0))
    h = health.get(engine.name)
    # success_rate in [0, 1]; treat fresh engines (total=0) as 0.5 so they
    # don't drown out engines with proven track records, but aren't frozen
    # out either.
    sr = h.success_rate if h.total > 0 else 0.5
    # Latency invert: faster engines rank higher. Clamp the EMA so a fresh
    # engine (ema=0) doesn't divide by zero / infinity.
    latency = max(h.latency_ema_ms, 50.0)
    latency_factor = 1000.0 / latency  # 1s → 1.0; 100ms → 10.0
    return weight * sr * latency_factor


def plan_waves(
    engines: list[t.Any],
    health: t.Any,
    *,
    explicit: bool = False,
) -> tuple[list[t.Any], list[t.Any]]:
    """Decide which engines run in the first vs second wave.

    Args:
        engines: Active engine modules (already loaded, not in cooldown).
        health: EngineHealthRegistry-like object with .get(name).
        explicit: True when the caller passed engines=[...] directly.
            Bypasses wave splitting — everything goes in wave one.

    Returns:
        (first_wave, second_wave). second_wave is empty when explicit
        is True or when there are no overflow general engines.
    """
    if explicit:
        return list(engines), []

    # Split by category: general vs vertical.
    general: list[t.Any] = []
    vertical: list[t.Any] = []
    for eng in engines:
        cats = getattr(eng, "categories", ["general"]) or ["general"]
        if "general" in cats:
            general.append(eng)
        else:
            vertical.append(eng)

    # Rank general engines by priority and split.
    general_sorted = sorted(general, key=lambda e: _priority(e, health), reverse=True)
    first_general = general_sorted[:GENERAL_FIRST_WAVE]
    overflow_general = general_sorted[GENERAL_FIRST_WAVE:GENERAL_FIRST_WAVE + GENERAL_SECOND_WAVE]

    # Vertical engines always run in wave one.
    first_wave = first_general + vertical
    second_wave = overflow_general
    return first_wave, second_wave


def coverage_satisfied(result_count: int, unique_domains: int, unique_engines: int) -> bool:
    """True when first-wave results are enough; False triggers wave two.

    Any single condition failing returns False — we want diversity in
    domains AND engines, not just raw count.
    """
    return (
        result_count >= MIN_RESULTS
        and unique_domains >= MIN_UNIQUE_DOMAINS
        and unique_engines >= MIN_UNIQUE_ENGINES
    )
