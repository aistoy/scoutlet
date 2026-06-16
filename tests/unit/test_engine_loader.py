"""Unit tests for engine_loader."""

import types
import pytest
from pathlib import Path
from unittest.mock import patch

from scoutlet.engine_loader import (
    load_engine,
    load_engines,
    list_available_engines,
    register_engine,
    engines,
    categories,
    BUNDLED_ENGINE_DIR,
    ENGINE_DEFAULTS,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear global engine registry before each test."""
    engines.clear()
    categories.clear()
    categories["general"] = []
    yield
    engines.clear()
    categories.clear()
    categories["general"] = []


class TestLoadBundledEngine:
    def test_load_bing(self):
        eng = load_engine("bing")
        assert eng is not None
        assert eng.name == "bing"
        assert "general" in eng.categories

    def test_load_google(self):
        eng = load_engine("google")
        assert eng is not None
        assert eng.name == "google"
        assert "general" in eng.categories

    def test_load_nonexistent_returns_none(self):
        eng = load_engine("nonexistent_engine_xyz")
        assert eng is None

    def test_engine_gets_defaults(self):
        eng = load_engine("bing")
        assert hasattr(eng, "timeout")
        assert eng.timeout == ENGINE_DEFAULTS["timeout"]
        assert hasattr(eng, "weight")
        assert eng.fallback_to_browser is False

    def test_engine_overrides_applied(self):
        eng = load_engine("bing", weight=5.0, timeout=20.0)
        assert eng.weight == 5.0
        assert eng.timeout == 20.0


class TestLoadEngines:
    def test_load_specific_engines(self):
        result = load_engines(engine_names=["bing", "brave"])
        assert "bing" in result
        assert "brave" in result
        assert len(result) == 2

    def test_load_all_bundled(self):
        result = load_engines()
        assert len(result) > 10

    def test_load_with_configs(self):
        result = load_engines(
            engine_names=["bing"],
            engine_configs={"bing": {"weight": 3.0}},
        )
        assert result["bing"].weight == 3.0

    def test_load_from_explicit_dir(self):
        result = load_engines(engine_dir=str(BUNDLED_ENGINE_DIR))
        assert "bing" in result


class TestRegisterEngine:
    def test_register_adds_to_engines(self):
        eng = types.ModuleType("test_eng")
        eng.name = "test_eng"
        eng.categories = ["general"]
        register_engine(eng)
        assert "test_eng" in engines

    def test_register_adds_to_categories(self):
        eng = types.ModuleType("test_eng")
        eng.name = "test_eng"
        eng.categories = ["general", "news"]
        register_engine(eng)
        assert eng in categories["general"]
        assert eng in categories["news"]


class TestListAvailableEngines:
    def test_list_bundled(self):
        names = list_available_engines()
        assert "bing" in names
        assert "google" in names
        assert "duckduckgo" in names

    def test_list_from_dir(self):
        names = list_available_engines(engine_dir=str(BUNDLED_ENGINE_DIR))
        assert "bing" in names
