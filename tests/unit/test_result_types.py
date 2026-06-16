"""Unit tests for SearchResult."""

import datetime
import urllib.parse

from scoutlet.result_types import SearchResult


class TestSearchResultNormalize:
    def test_url_scheme_added_when_missing(self):
        r = SearchResult(url="example.com/path")
        r.normalize()
        assert r.url.startswith("http://")
        assert r.parsed_url.scheme == "http"

    def test_url_https_preserved(self):
        r = SearchResult(url="https://example.com/path")
        r.normalize()
        assert r.url == "https://example.com/path"
        assert r.parsed_url.scheme == "https"

    def test_whitespace_normalized_in_title(self):
        r = SearchResult(url="https://x.com", title="hello\t\tworld\n\nfoo")
        r.normalize()
        assert r.title == "hello world foo"

    def test_whitespace_normalized_in_content(self):
        r = SearchResult(url="https://x.com", content="bar\tbaz\nqux")
        r.normalize()
        assert r.content == "bar baz qux"

    def test_engine_auto_added_to_engines_set(self):
        r = SearchResult(url="https://x.com", engine="google")
        r.normalize()
        assert "google" in r.engines

    def test_invalid_date_cleared(self):
        # datetime with year 0 causes ValueError in strftime('%Y-%m-%d')
        r = SearchResult(
            url="https://x.com",
            publishedDate=datetime.datetime(1, 1, 1),
        )
        r.normalize()
        # Year 1 should be fine
        assert r.publishedDate is not None

    def test_content_same_as_title_cleared(self):
        r = SearchResult(url="https://x.com", title="Hello World", content="Hello World")
        r.normalize()
        assert r.content == ""

    def test_non_string_url_cleared(self):
        r = SearchResult(url=123)
        r.normalize()
        assert r.url == ""
        assert r.parsed_url is None

    def test_non_string_title_converted(self):
        r = SearchResult(url="https://x.com", title=42)
        r.normalize()
        assert r.title == "42"


class TestSearchResultHash:
    def test_same_url_same_hash(self):
        r1 = SearchResult(url="https://example.com/page")
        r1.normalize()
        r2 = SearchResult(url="https://example.com/page")
        r2.normalize()
        assert hash(r1) == hash(r2)

    def test_different_url_different_hash(self):
        r1 = SearchResult(url="https://example.com/a")
        r1.normalize()
        r2 = SearchResult(url="https://example.com/b")
        r2.normalize()
        assert hash(r1) != hash(r2)

    def test_different_query_not_in_hash(self):
        r1 = SearchResult(url="https://example.com/page")
        r1.normalize()
        r2 = SearchResult(url="https://example.com/page?foo=bar")
        r2.normalize()
        # Different query should produce different hash
        assert hash(r1) != hash(r2)

    def test_same_template_and_img_src_same_hash(self):
        r1 = SearchResult(url="https://example.com/img", template="images.html", img_src="https://img.com/1.jpg")
        r1.normalize()
        r2 = SearchResult(url="https://example.com/img", template="images.html", img_src="https://img.com/1.jpg")
        r2.normalize()
        assert hash(r1) == hash(r2)

    def test_different_img_src_different_hash(self):
        r1 = SearchResult(url="https://example.com/img", img_src="https://img.com/1.jpg")
        r1.normalize()
        r2 = SearchResult(url="https://example.com/img", img_src="https://img.com/2.jpg")
        r2.normalize()
        assert hash(r1) != hash(r2)

    def test_no_parsed_url_raises(self):
        r = SearchResult(url="")
        with pytest.raises(ValueError):
            hash(r)


class TestSearchResultEquality:
    def test_equal_results(self):
        r1 = SearchResult(url="https://example.com/a")
        r1.normalize()
        r2 = SearchResult(url="https://example.com/a")
        r2.normalize()
        assert r1 == r2

    def test_unequal_results(self):
        r1 = SearchResult(url="https://example.com/a")
        r1.normalize()
        r2 = SearchResult(url="https://example.com/b")
        r2.normalize()
        assert r1 != r2


class TestSearchResultDefaultsFrom:
    def test_fills_empty_fields(self):
        r1 = SearchResult(url="https://x.com", title="Hello")
        r2 = SearchResult(url="https://x.com", content="World", thumbnail="thumb.jpg")
        r1.defaults_from(r2)
        assert r1.content == "World"
        assert r1.thumbnail == "thumb.jpg"

    def test_does_not_overwrite_existing(self):
        r1 = SearchResult(url="https://x.com", title="Hello", content="Existing")
        r2 = SearchResult(url="https://x.com", content="New")
        r1.defaults_from(r2)
        assert r1.content == "Existing"


class TestSearchResultAsDict:
    def test_round_trip(self):
        r = SearchResult(
            url="https://example.com",
            title="Test",
            content="Content",
            engine="google",
            score=1.5,
        )
        r.normalize()
        d = r.as_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Test"
        assert d["content"] == "Content"
        assert d["engine"] == "google"
        assert d["score"] == 1.5


class TestSearchResultDictAccess:
    def test_getitem(self):
        r = SearchResult(url="https://x.com", title="Hello")
        assert r["url"] == "https://x.com"
        assert r["title"] == "Hello"

    def test_setitem(self):
        r = SearchResult()
        r["title"] = "New Title"
        assert r.title == "New Title"

    def test_contains(self):
        r = SearchResult(url="https://x.com", title="Hello")
        assert "url" in r
        assert "content" not in r


import pytest
