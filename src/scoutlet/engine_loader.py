"""Engine loader for scoutlet.

Engine loading priority:
  1. External dir (~/.scoutlet/engines/) — hot-updated / user-added engines
  2. Bundled dir (src/scoutlet/engines/) — built-in fallback

External dir overrides bundled for same-named engines.
External-only engines (not in bundled) are also loaded.
"""

from __future__ import annotations

import copy
import importlib
import importlib.util
import types
import typing as t
from pathlib import Path

from scoutlet.traits import EngineTraitsMap

import logging

log = logging.getLogger("scoutlet.engine_loader")

# Bundled engine directory (shipped with package)
BUNDLED_ENGINE_DIR = Path(__file__).parent / "engines"

# External engine directory (hot-updated engines)
EXTERNAL_ENGINE_DIR = Path.home() / ".scoutlet" / "engines"

ENGINE_DEFAULTS: dict[str, t.Any] = {
    "engine_type": "online",
    "paging": False,
    "time_range_support": False,
    "safesearch": False,
    "categories": ["general"],
    "enable_http": False,
    "shortcut": "-",
    "timeout": 10.0,
    "display_error_messages": True,
    "disabled": False,
    "inactive": False,
    "about": {},
    "using_tor_proxy": False,
    "proxies": None,
    "fallback_to_browser": False,
    "cdp_endpoint": "http://localhost:9222",
    "auto_launch_browser": False,
    "headless": True,
    "browser_args": None,
    "block_resources": True,
    "send_accept_language_header": True,
    "tokens": [],
    "max_page": 0,
    "weight": 1,
    "language_support": False,
    "http_client": "",
}

# Global engine registry
engines: dict[str, types.ModuleType] = {}
categories: dict[str, list[types.ModuleType]] = {"general": []}

_traits_map: EngineTraitsMap | None = None


def _get_traits_map() -> EngineTraitsMap:
    global _traits_map
    if _traits_map is None:
        _traits_map = EngineTraitsMap.from_data()
    return _traits_map


def load_module(filename: str, module_dir: str) -> types.ModuleType:
    """Load a Python module from file path."""
    modname = Path(filename).stem
    modpath = str(Path(module_dir) / filename)
    spec = importlib.util.spec_from_file_location(modname, modpath)
    if not spec or not spec.loader:
        raise ValueError(f"Error loading '{modpath}' module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_engine_dir(name: str, engine_dir: str | Path | None = None) -> Path | None:
    """Resolve which directory to load an engine from.

    Priority: explicit engine_dir > external dir > bundled dir
    Returns None if engine file not found anywhere.
    """
    if engine_dir is not None:
        p = Path(engine_dir) / (name + ".py")
        return Path(engine_dir) if p.exists() else None

    # Check external dir first
    ext_file = EXTERNAL_ENGINE_DIR / (name + ".py")
    if ext_file.exists():
        return EXTERNAL_ENGINE_DIR

    # Fallback to bundled dir
    bundled_file = BUNDLED_ENGINE_DIR / (name + ".py")
    if bundled_file.exists():
        return BUNDLED_ENGINE_DIR

    return None


def load_engine(name: str, engine_dir: str | Path | None = None, **overrides: t.Any) -> types.ModuleType | None:
    """Load a single engine module.

    Args:
        name: Engine name (matches .py filename without extension)
        engine_dir: Explicit directory to load from. If None, auto-resolves
                    (external dir overrides bundled).
        **overrides: Additional attributes to set on the engine module

    Returns:
        Loaded engine module or None if loading failed
    """
    if engine_dir is not None:
        resolved_dir = Path(engine_dir)
    else:
        resolved_dir = _resolve_engine_dir(name)
        if resolved_dir is None:
            log.error("Engine file not found: %s", name)
            return None

    filename = name + ".py"

    if not (resolved_dir / filename).exists():
        log.error("Engine file not found: %s/%s", resolved_dir, filename)
        return None

    try:
        engine = load_module(filename, str(resolved_dir))
    except Exception:
        log.exception("Cannot load engine '%s'", name)
        return None

    # Set name
    engine.name = overrides.pop("name", name)

    # Apply defaults
    for arg_name, arg_value in ENGINE_DEFAULTS.items():
        if not hasattr(engine, arg_name):
            setattr(engine, arg_name, copy.deepcopy(arg_value))

    # Apply overrides
    for key, value in overrides.items():
        setattr(engine, key, value)

    # Load traits from engine_traits.json
    try:
        traits_map = _get_traits_map()
        traits_map.set_traits(engine)
    except Exception:
        log.warning("Failed to load traits for engine '%s'", name, exc_info=True)

    # Call engine.setup() if it exists
    setup_func = getattr(engine, "setup", None)
    if setup_func and callable(setup_func):
        try:
            if not setup_func({"name": name, "engine": name}):
                log.error("Engine '%s' setup failed", name)
                return None
        except Exception:
            log.exception("Engine '%s' setup exception", name)
            return None

    return engine


def _discover_engines() -> list[str]:
    """Discover all engine names from bundled + external directories."""
    names: set[str] = set()
    for d in (BUNDLED_ENGINE_DIR, EXTERNAL_ENGINE_DIR):
        if d.is_dir():
            names.update(
                p.stem for p in d.glob("*.py")
                if p.stem != "__init__" and not p.stem.startswith("_")
            )
    return sorted(names)


def load_engines(
    engine_names: list[str] | None = None,
    engine_dir: str | Path | None = None,
    engine_configs: dict[str, dict[str, t.Any]] | None = None,
) -> dict[str, types.ModuleType]:
    """Load multiple engines and register them.

    Args:
        engine_names: List of engine names to load. If None, discover all
                      from bundled + external directories.
        engine_dir: Explicit directory. If set, only load from this dir
                    (skip auto-resolution).
        engine_configs: Optional per-engine config overrides {name: {key: val}}

    Returns:
        Dictionary of loaded engines {name: module}
    """
    engine_configs = engine_configs or {}

    engines.clear()
    categories.clear()
    categories["general"] = []

    if engine_dir is not None:
        # Explicit dir: only load from here
        engine_dir = Path(engine_dir)
        if engine_names is None:
            engine_names = sorted(
                p.stem for p in engine_dir.glob("*.py")
                if p.stem != "__init__" and not p.stem.startswith("_")
            )
        for name in engine_names:
            config = engine_configs.get(name, {})
            engine = load_engine(name, engine_dir, **config)
            if engine:
                register_engine(engine)
    else:
        # Auto-resolve: discover from bundled + external
        if engine_names is None:
            engine_names = _discover_engines()
        for name in engine_names:
            config = engine_configs.get(name, {})
            engine = load_engine(name, None, **config)
            if engine:
                register_engine(engine)

    return engines


def register_engine(engine: types.ModuleType) -> None:
    """Register a loaded engine in the global registry."""
    name = engine.name
    if name in engines:
        log.warning("Engine '%s' already registered, overwriting", name)

    engines[name] = engine

    for category in engine.categories:
        categories.setdefault(category, []).append(engine)


def list_available_engines(engine_dir: str | Path | None = None) -> list[str]:
    """List available engine names.

    If engine_dir is specified, list from that dir only.
    Otherwise, discover from bundled + external directories.
    """
    if engine_dir is not None:
        engine_dir = Path(engine_dir)
        return sorted(
            p.stem for p in engine_dir.glob("*.py")
            if p.stem != "__init__" and not p.stem.startswith("_")
        )
    return _discover_engines()


def get_engine(name: str) -> types.ModuleType | None:
    """Get a loaded engine by name."""
    return engines.get(name)
