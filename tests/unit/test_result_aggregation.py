"""Unit tests for ResultContainer and aggregation logic."""

import types
import pytest

from scoutlet.result_types import SearchResult
from scoutlet.result_aggregation import (
    ResultContainer,
    calculate_score,
    merge_two_results,
    HEALTH_PENALTY,
    UNIQUE_BONUS,
)
from scoutlet.health import EngineHealth, EngineHealthRegistry
from scoutlet.outcome import FailureKind


def _make_engine(name: str, weight: float = 1.0, categories: list[str] | None = None):
    """Create a mock engine module."""
    eng = types.ModuleType(name)
    eng.name = name
    eng.weight = weight
    eng.categories = categories or ["general"]
    return eng


def _registry_with(engine: str, **health_kwargs) -> EngineHealthRegistry:
    """Build a registry where `engine` has the given health attributes."""
    reg = EngineHealthRegistry()
    h = reg.get(engine)
    for k, v in health_kwargs.items():
        setattr(h, k, v)
    return reg


class TestCalculateScore:
    def test_single_position(self):
        r = SearchResult(url="https://x.com", engine="google")
        r.normalize()
        r.positions = [1]
        eng = _make_engine("google", weight=2.0)
        score = calculate_score(r, {"google": eng})
        # weight=2.0, positions=[1], normal priority: 2.0 * 1/1 = 2.0
        assert score == 2.0

    def test_multiple_positions(self):
        r = SearchResult(url="https://x.com", engine="google")
        r.normalize()
        r.positions = [1, 2]
        eng = _make_engine("google", weight=1.0)
        score = calculate_score(r, {"google": eng})
        # weight=1.0*2=2.0, score = 2.0/1 + 2.0/2 = 2.0+1.0 = 3.0
        assert score == 3.0

    def test_multi_engine_corroboration(self):
        r = SearchResult(url="https://x.com", engine="google")
        r.normalize()
        r.engines = {"google", "bing"}
        r.positions = [1, 2]
        g = _make_engine("google", weight=1.0)
        b = _make_engine("bing", weight=1.0)
        score = calculate_score(r, {"google": g, "bing": b})
        # weight=1.0*1.0*2=2.0, score=2.0/1+2.0/2=3.0
        assert score == 3.0

    def test_engine_weight_multiplies(self):
        r = SearchResult(url="https://x.com", engine="google")
        r.normalize()
        r.positions = [1]
        eng = _make_engine("google", weight=3.0)
        score = calculate_score(r, {"google": eng})
        # weight=3.0, score=3.0/1=3.0
        assert score == 3.0

    def test_high_priority_adds_weight(self):
        r = SearchResult(url="https://x.com", engine="google", priority="high")
        r.normalize()
        r.positions = [1, 2]
        eng = _make_engine("google", weight=1.0)
        score = calculate_score(r, {"google": eng})
        # weight=1.0*2=2.0, high priority: score=2.0+2.0=4.0
        assert score == 4.0

    def test_low_priority_zero_score(self):
        r = SearchResult(url="https://x.com", engine="google", priority="low")
        r.normalize()
        r.positions = [1, 2, 3]
        eng = _make_engine("google", weight=5.0)
        score = calculate_score(r, {"google": eng})
        assert score == 0.0


class TestMergeTwoResults:
    def test_longer_content_kept(self):
        r1 = SearchResult(url="https://x.com", content="Short")
        r2 = SearchResult(url="https://x.com", content="Longer content here")
        r1.normalize()
        r2.normalize()
        merge_two_results(r1, r2)
        assert r1.content == "Longer content here"

    def test_longer_title_kept(self):
        r1 = SearchResult(url="https://x.com", title="A")
        r2 = SearchResult(url="https://x.com", title="A Longer Title")
        r1.normalize()
        r2.normalize()
        merge_two_results(r1, r2)
        assert r1.title == "A Longer Title"

    def test_engines_merged(self):
        r1 = SearchResult(url="https://x.com", engine="google")
        r2 = SearchResult(url="https://x.com", engine="bing")
        r1.normalize()
        r2.normalize()
        merge_two_results(r1, r2)
        assert r1.engines == {"google", "bing"}

    def test_https_preferred(self):
        r1 = SearchResult(url="http://example.com/page")
        r2 = SearchResult(url="https://example.com/page")
        r1.normalize()
        r2.normalize()
        merge_two_results(r1, r2)
        assert r1.url.startswith("https://")

    def test_http_not_downgraded(self):
        r1 = SearchResult(url="https://example.com/page")
        r2 = SearchResult(url="http://example.com/page")
        r1.normalize()
        r2.normalize()
        merge_two_results(r1, r2)
        assert r1.url.startswith("https://")


class TestResultContainer:
    def test_extend_single_engine(self):
        container = ResultContainer()
        results = [
            SearchResult(url="https://a.com", title="A"),
            SearchResult(url="https://b.com", title="B"),
        ]
        container.extend("google", results)
        container.close()
        ordered = container.get_ordered_results()
        assert len(ordered) == 2

    def test_deduplication_by_url(self):
        container = ResultContainer()
        r1 = SearchResult(url="https://example.com/page", title="From Google", engine="google")
        r2 = SearchResult(url="https://example.com/page", title="From Bing", engine="bing")
        container.extend("google", [r1])
        container.extend("bing", [r2])
        container.close()
        ordered = container.get_ordered_results()
        assert len(ordered) == 1
        assert "google" in ordered[0].engines
        assert "bing" in ordered[0].engines

    def test_engine_positions_populated_on_first_insert(self):
        container = ResultContainer()
        r1 = SearchResult(url="https://example.com/p1", engine="google")
        r2 = SearchResult(url="https://example.com/p2", engine="google")
        container.extend("google", [r1, r2])
        container.close()
        ordered = sorted(container.get_ordered_results(), key=lambda r: r.url)
        # Position is 1-indexed within the engine's batch.
        assert ordered[0].engine_positions == {"google": 1}
        assert ordered[1].engine_positions == {"google": 2}

    def test_engine_positions_merges_across_engines(self):
        container = ResultContainer()
        r1 = SearchResult(url="https://example.com/page", engine="google")
        r2 = SearchResult(url="https://example.com/page", engine="bing")
        container.extend("google", [r1])  # position 1
        container.extend("bing", [r2])    # position 1 in bing's batch
        container.close()
        ordered = container.get_ordered_results()
        assert len(ordered) == 1
        # Both engines contributed, each with their own position.
        assert ordered[0].engine_positions == {"google": 1, "bing": 1}
        assert ordered[0].corroboration_count == 2

    def test_longer_content_wins_on_merge(self):
        container = ResultContainer()
        r1 = SearchResult(url="https://x.com", title="Test", content="Short", engine="google")
        r2 = SearchResult(url="https://x.com", title="Test", content="Much longer content", engine="bing")
        container.extend("google", [r1])
        container.extend("bing", [r2])
        container.close()
        ordered = container.get_ordered_results()
        assert len(ordered) == 1
        assert ordered[0].content == "Much longer content"

    def test_engine_weight_affects_order(self):
        g = _make_engine("google", weight=2.0)
        b = _make_engine("bing", weight=1.0)
        container = ResultContainer(engines_registry={"google": g, "bing": b})
        r1 = SearchResult(url="https://a.com", title="A", engine="google")
        r2 = SearchResult(url="https://b.com", title="B", engine="bing")
        container.extend("google", [r1])
        container.extend("bing", [r2])
        container.close()
        ordered = container.get_ordered_results()
        assert ordered[0].url == "https://a.com"

    def test_category_grouping(self):
        g = _make_engine("google", categories=["general"])
        n = _make_engine("bing_news", categories=["news"])
        container = ResultContainer(engines_registry={"google": g, "bing_news": n})
        # Add many general results
        for i in range(10):
            r = SearchResult(url=f"https://gen{i}.com", title=f"Gen {i}", engine="google")
            container.extend("google", [r])
        # Add a news result
        r = SearchResult(url="https://news.com", title="Breaking", engine="bing_news")
        container.extend("bing_news", [r])
        container.close()
        ordered = container.get_ordered_results()
        assert len(ordered) == 11

    def test_dict_results_converted(self):
        container = ResultContainer()
        container.extend("google", [{"url": "https://x.com", "title": "Dict Result"}])
        container.close()
        ordered = container.get_ordered_results()
        assert len(ordered) == 1
        assert ordered[0].title == "Dict Result"

    def test_closed_container_rejects_new_results(self):
        container = ResultContainer()
        container.close()
        container.extend("google", [SearchResult(url="https://x.com", title="Late")])
        ordered = container.get_ordered_results()
        assert len(ordered) == 0


class TestScoreAdjustments:
    """Diversity bonus + health penalty layered on top of SearXNG base."""

    def test_unique_result_gets_bonus_when_registry_present(self):
        g = _make_engine("google", weight=1.0)
        reg = EngineHealthRegistry()  # fresh: engines start healthy
        container = ResultContainer(engines_registry={"google": g}, health_registry=reg)
        r = SearchResult(url="https://unique.com", title="U", engine="google")
        container.extend("google", [r])
        container.close()
        ordered = container.get_ordered_results()
        # Base score = weight(1.0) * len(positions)(1) * 1/position(1) = 1.0
        # Adjusted: 1.0 * UNIQUE_BONUS
        assert ordered[0].score == pytest.approx(UNIQUE_BONUS)

    def test_unique_result_no_bonus_when_registry_absent(self):
        """Backwards-compat: callers that don't pass a health registry
        get the original SearXNG base score only."""
        g = _make_engine("google", weight=1.0)
        container = ResultContainer(engines_registry={"google": g})
        r = SearchResult(url="https://unique.com", title="U", engine="google")
        container.extend("google", [r])
        container.close()
        ordered = container.get_ordered_results()
        assert ordered[0].score == pytest.approx(1.0)

    def test_corroborated_result_unadjusted(self):
        """Multi-engine results are trusted; no bonus, no penalty."""
        g = _make_engine("google", weight=1.0)
        b = _make_engine("bing", weight=1.0)
        reg = EngineHealthRegistry()
        container = ResultContainer(
            engines_registry={"google": g, "bing": b},
            health_registry=reg,
        )
        r1 = SearchResult(url="https://corroborated.com", title="C", engine="google")
        r2 = SearchResult(url="https://corroborated.com", title="C", engine="bing")
        container.extend("google", [r1])
        container.extend("bing", [r2])
        container.close()
        ordered = container.get_ordered_results()
        # Two engines at position 1 each:
        #   weight = 1 * 1 * len([1,1]) = 2
        #   score = 2/1 + 2/1 = 4.0
        assert ordered[0].score == pytest.approx(4.0)

    def test_bad_engine_unique_result_penalized(self):
        g = _make_engine("google", weight=1.0)
        reg = _registry_with("google", cooldown_until=float("inf"))
        # cooldown_until in future makes is_bad True
        import time
        reg.get("google").cooldown_until = time.time() + 1000

        container = ResultContainer(engines_registry={"google": g}, health_registry=reg)
        r = SearchResult(url="https://x.com", title="X", engine="google")
        container.extend("google", [r])
        container.close()
        ordered = container.get_ordered_results()
        # Base 1.0 * HEALTH_PENALTY (is_bad path skips UNIQUE_BONUS)
        assert ordered[0].score == pytest.approx(HEALTH_PENALTY)

    def test_low_success_rate_engine_penalized(self):
        """Engine with < 0.3 success rate over enough samples is bad."""
        g = _make_engine("flaky", weight=1.0)
        reg = _registry_with(
            "flaky",
            success_count=1,
            failure_count=9,
        )
        assert reg.get("flaky").is_bad is True  # sanity

        container = ResultContainer(engines_registry={"flaky": g}, health_registry=reg)
        r = SearchResult(url="https://flaky.com", title="F", engine="flaky")
        container.extend("flaky", [r])
        container.close()
        ordered = container.get_ordered_results()
        assert ordered[0].score == pytest.approx(HEALTH_PENALTY)

    def test_bad_engine_corroborated_result_not_penalized(self):
        """If a healthy engine corroborates, we trust the result."""
        g = _make_engine("flaky", weight=1.0)
        b = _make_engine("bing", weight=1.0)
        reg = _registry_with("flaky", success_count=1, failure_count=9)
        container = ResultContainer(
            engines_registry={"flaky": g, "bing": b},
            health_registry=reg,
        )
        r1 = SearchResult(url="https://shared.com", title="S", engine="flaky")
        r2 = SearchResult(url="https://shared.com", title="S", engine="bing")
        container.extend("flaky", [r1])
        container.extend("bing", [r2])
        container.close()
        ordered = container.get_ordered_results()
        # Multi-engine: base only, no penalty (flaky bad but bing is healthy)
        # weight = 1*1*2 = 2, score = 2/1 + 2/1 = 4.0
        assert ordered[0].score == pytest.approx(4.0)

    def test_bonus_can_flip_ordering(self):
        """Unique result from healthy engine beats corroborated result
        from low-weight engines once bonus is applied."""
        # Healthy unique-result engine: weight=2
        g = _make_engine("google", weight=2.0)
        # Low-weight corroboration pair
        m1 = _make_engine("mwmbl", weight=0.1)
        m2 = _make_engine("marginalia", weight=0.1)
        reg = EngineHealthRegistry()
        container = ResultContainer(
            engines_registry={"google": g, "mwmbl": m1, "marginalia": m2},
            health_registry=reg,
        )
        # Google's unique result at position 2
        container.extend("google", [
            SearchResult(url="https://unique.com", title="U", engine="google")
        ])
        # Two-engine corroborated result at position 1
        r1 = SearchResult(url="https://shared.com", title="S", engine="mwmbl")
        r2 = SearchResult(url="https://shared.com", title="S", engine="marginalia")
        container.extend("mwmbl", [r1])
        container.extend("marginalia", [r2])
        container.close()
        ordered = container.get_ordered_results()
        # Google unique: base = 2*1*1/1 = 2.0, adjusted * 1.2 = 2.4
        # Corroborated: base = 0.1*0.1*2 * (1/1 + 1/1) = 0.02 * 2 = 0.04
        assert ordered[0].url == "https://unique.com"
        assert ordered[0].score == pytest.approx(2.4, rel=0.001)
