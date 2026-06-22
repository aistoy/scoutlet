"""Shared fixtures for mock-HTTP integration tests.

These tests drive the full ``search()`` pipeline against scripted HTTP
responses via respx. The autouse ``reset_health`` fixture clears the
module-level health registry between tests so cooldowns don't leak.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import respx

from scoutlet.health import reset_default_registry
from scoutlet import network

FIXTURES = Path(__file__).parent.parent / "fixtures" / "engines"


@pytest.fixture
def respx_mock():
    """Active respx mock scope. Real httpx calls inside raise."""
    with respx.mock(assert_all_called=False) as mock:
        yield mock


@pytest.fixture(autouse=True)
def reset_health():
    """Clear health registry + close cached adapters before each test.

    Health registry is module-level; without this, a cooldown from one
    test bleeds into the next. Cached httpx clients are also reset so
    respx's transport patches apply to a fresh client each test.
    """
    reset_default_registry()
    network.close()
    yield
    network.close()


@pytest.fixture
def bing_success_html() -> str:
    return (FIXTURES / "bing" / "success_minimal.html").read_text()


@pytest.fixture
def bing_captcha_html() -> str:
    return (FIXTURES / "bing" / "captcha_minimal.html").read_text()
