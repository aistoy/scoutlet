"""Engine traits for scoutlet, simplified from SearXNG's enginelib/traits.py."""

from __future__ import annotations

import dataclasses
import json
import types
import typing as t
from pathlib import Path

from scoutlet import locales

import logging

log = logging.getLogger("scoutlet.traits")

_DATA_DIR = Path(__file__).parent / "data"


@dataclasses.dataclass
class EngineTraits:
    """Traits for a search engine (languages, regions, custom data)."""

    regions: dict[str, str] = dataclasses.field(default_factory=dict)
    languages: dict[str, str] = dataclasses.field(default_factory=dict)
    all_locale: str | None = None
    data_type: t.Literal["traits_v1"] = "traits_v1"
    custom: dict[str, t.Any] = dataclasses.field(default_factory=dict)

    def get_language(self, searxng_locale: str, default: str | None = None) -> str | None:
        """Return engine's language string that best fits to locale."""
        if searxng_locale == "all" and self.all_locale is not None:
            return self.all_locale
        return locales.get_engine_locale(searxng_locale, self.languages, default=default)

    def get_region(self, searxng_locale: str, default: str | None = None) -> str | None:
        """Return engine's region string that best fits to locale."""
        if searxng_locale == "all" and self.all_locale is not None:
            return self.all_locale
        return locales.get_engine_locale(searxng_locale, self.regions, default=default)

    def is_locale_supported(self, searxng_locale: str) -> bool:
        if self.data_type == "traits_v1":
            return bool(self.get_region(searxng_locale) or self.get_language(searxng_locale))
        raise TypeError("engine traits of type %s is unknown" % self.data_type)

    def copy(self):
        return EngineTraits(**dataclasses.asdict(self))

    def set_traits(self, engine: types.ModuleType) -> None:
        """Set traits from self in engine namespace."""
        traits = self.copy()
        engine.language_support = bool(traits.languages or traits.regions)
        engine.traits = traits


class EngineTraitsMap(dict[str, EngineTraits]):
    """Map EngineTraits by engine name."""

    @classmethod
    def from_data(cls) -> EngineTraitsMap:
        """Load traits from bundled engine_traits.json."""
        obj = cls()
        traits_file = _DATA_DIR / "engine_traits.json"
        if not traits_file.exists():
            log.warning("engine_traits.json not found at %s", traits_file)
            return obj
        with open(traits_file, encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            obj[k] = EngineTraits(**v)
        return obj

    def set_traits(self, engine: types.ModuleType) -> None:
        """Set traits for an engine if available."""
        engine_name = getattr(engine, "name", getattr(engine, "__name__", ""))
        traits = self.get(engine_name)
        # Fallback: SearXNG uses spaces in keys (e.g. "google images")
        # while module names use underscores (e.g. "google_images")
        if traits is None:
            traits = self.get(engine_name.replace("_", " "))
        # Fallback: duckduckgo_extra shares traits with duckduckgo
        if traits is None and "_extra" in engine_name:
            base = engine_name.replace("_extra", "")
            traits = self.get(base) or self.get(base.replace("_", " "))
        if traits:
            traits.set_traits(engine)
