"""Result types for scoutlet, simplified from SearXNG's MainResult/LegacyResult."""

from __future__ import annotations

import re
import urllib.parse
import datetime
from dataclasses import dataclass, field

import logging

log = logging.getLogger("scoutlet.result_types")

WHITESPACE_REGEX = re.compile('( |\t|\n)+', re.M | re.U)


@dataclass
class SearchResult:
    """A single search result, compatible with SearXNG's MainResult interface."""

    url: str = ""
    title: str = ""
    content: str = ""
    engine: str = ""
    engines: set[str] = field(default_factory=set)
    score: float = 0
    positions: list[int] = field(default_factory=list)
    template: str = "default.html"
    img_src: str = ""
    iframe_src: str = ""
    audio_src: str = ""
    thumbnail: str = ""
    publishedDate: datetime.datetime | None = None
    author: str = ""
    metadata: str = ""
    category: str = ""
    priority: str = ""  # "", "high", "low"

    # Computed fields
    parsed_url: urllib.parse.ParseResult | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.url and not self.parsed_url:
            if isinstance(self.url, str):
                self.parsed_url = urllib.parse.urlparse(self.url)

    def normalize(self):
        """Normalize URL and text fields, mirroring SearXNG's normalize_result_fields."""
        # Normalize URL
        if self.url and not self.parsed_url:
            if not isinstance(self.url, str):
                self.url = ""
                self.parsed_url = None
            else:
                self.parsed_url = urllib.parse.urlparse(self.url)

        if self.parsed_url:
            self.parsed_url = self.parsed_url._replace(
                scheme=self.parsed_url.scheme or "http",
                path=self.parsed_url.path,
            )
            self.url = self.parsed_url.geturl()

        # Normalize text
        if self.title and not isinstance(self.title, str):
            self.title = str(self.title)
        if self.content and not isinstance(self.content, str):
            self.content = str(self.content)
        if self.title:
            self.title = WHITESPACE_REGEX.sub(" ", self.title).strip()
        if self.content:
            self.content = WHITESPACE_REGEX.sub(" ", self.content).strip()
        if self.content == self.title:
            self.content = ""

        # Add engine to engines set
        if self.engine:
            self.engines.add(self.engine)

        # Normalize date
        if self.publishedDate:
            try:
                self.publishedDate.strftime('%Y-%m-%d')
            except ValueError:
                self.publishedDate = None

    def __hash__(self) -> int:
        """Hash for deduplication, same algorithm as SearXNG's MainResult.__hash__."""
        if not self.parsed_url:
            raise ValueError(f"missing parsed_url: {self}")
        url = self.parsed_url
        return hash(
            f"{self.template}"
            + f"|{url.netloc}|{url.path}|{url.params}|{url.query}|{url.fragment}"
            + f"|{self.img_src}"
        )

    def __eq__(self, other: object):
        return hash(self) == hash(other)

    def defaults_from(self, other: SearchResult):
        """Fill empty fields from another result."""
        for fname in ("url", "title", "content", "img_src", "thumbnail", "iframe_src",
                       "audio_src", "author", "metadata", "template", "category"):
            self_val = getattr(self, fname, "")
            other_val = getattr(other, fname, "")
            if not self_val and other_val:
                setattr(self, fname, other_val)

    def as_dict(self) -> dict:
        """Convert to plain dict for JSON serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "engine": self.engine,
            "engines": list(self.engines),
            "score": self.score,
            "template": self.template,
            "img_src": self.img_src,
            "thumbnail": self.thumbnail,
            "publishedDate": self.publishedDate.isoformat() if self.publishedDate else None,
            "author": self.author,
            "metadata": self.metadata,
            "category": self.category,
        }

    # Dict-like access for compatibility with engines that use dict syntax
    def __getitem__(self, key: str):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __setitem__(self, key: str, value):
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) and getattr(self, key) not in (None, "", [])


class EngineResults(list):
    """Result list returned by engine's response() function."""

    def add(self, result: SearchResult | dict):
        """Add a result. Dicts are converted to SearchResult."""
        if isinstance(result, dict):
            result = SearchResult(**{k: v for k, v in result.items()
                                     if k in SearchResult.__dataclass_fields__})
        self.append(result)
