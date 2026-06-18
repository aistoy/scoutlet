"""Tests for the no-args default engine resolution in search()."""

import pytest

from scoutlet.search import (
    _is_chinese_query,
    _resolve_default_engines,
    DEFAULT_ENGINES_BASE,
    DEFAULT_ENGINES_ZH_EXTRA,
    DEFAULT_ENGINES_NONZH_EXTRA,
)


class TestChineseQueryDetection:
    def test_pure_ascii_is_not_chinese(self):
        assert _is_chinese_query("python asyncio") is False
        assert _is_chinese_query("hello world") is False

    def test_han_only_is_chinese(self):
        assert _is_chinese_query("异步编程") is True
        assert _is_chinese_query("Python 教程") is True

    def test_han_with_kana_is_not_chinese(self):
        # Han + hiragana → Japanese
        assert _is_chinese_query("Python の非同期処理") is False
        # Han + katakana → Japanese
        assert _is_chinese_query("プログラミング言語") is False

    def test_hangul_only_is_not_chinese(self):
        assert _is_chinese_query("파이썬 프로그래밍") is False

    def test_empty_or_none(self):
        assert _is_chinese_query("") is False
        assert _is_chinese_query(None) is False  # type: ignore[arg-type]


class TestResolveDefaultEngines:
    def test_always_includes_base_set(self):
        for q in ("python asyncio", "异步编程", "hello"):
            engines = _resolve_default_engines(q)
            for base in DEFAULT_ENGINES_BASE:
                assert base in engines, f"{base} missing for query {q!r}"

    def test_chinese_query_uses_zh_extra(self):
        engines = _resolve_default_engines("Python 异步编程")
        for eng in DEFAULT_ENGINES_ZH_EXTRA:
            assert eng in engines
        # Chinese-specific engines should appear
        assert "baidu" in engines
        assert "sogou" in engines

    def test_non_chinese_query_uses_nonzh_extra(self):
        engines = _resolve_default_engines("python asyncio tutorial")
        for eng in DEFAULT_ENGINES_NONZH_EXTRA:
            assert eng in engines
        # Chinese-only engines should NOT appear
        assert "baidu" not in engines
        assert "sogou" not in engines

    def test_international_engines_in_both_paths(self):
        # brave and bing appear in both ZH and non-ZH defaults
        zh = _resolve_default_engines("异步编程")
        nonzh = _resolve_default_engines("async programming")
        assert "brave" in zh
        assert "brave" in nonzh
        assert "bing" in zh
        assert "bing" in nonzh

    def test_returns_a_copy_not_module_constant(self):
        a = _resolve_default_engines("test")
        b = _resolve_default_engines("test")
        a.append("hacked")
        assert "hacked" not in b, "resolve must return a fresh list"


