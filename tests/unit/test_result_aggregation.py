"""Unit tests for ResultContainer and aggregation logic."""

import types
import pytest

from scoutlet.result_types import SearchResult
from scoutlet.result_aggregation import ResultContainer, calculate_score, merge_two_results


def _make_engine(name: str, weight: float = 1.0, categories: list[str] | None = None):
    """Create a mock engine module."""
    eng = types.ModuleType(name)
    eng.name = name
    eng.weight = weight
    eng.categories = categories or ["general"]
    return eng


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
