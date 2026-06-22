"""Pure-HTTP block-page classifier.

Detects anti-bot / block pages from HTTP response body and URL alone — no
browser dependency. Used to label engine failures so callers (health checks,
routing, auto-heal) can distinguish "engine parser broken" from "engine got
CAPTCHA'd".

Three-tier detection:
  1. Engine-specific URL/body patterns (always checked)
  2. Generic anti-bot keywords (only on short pages < 2KB to avoid false positives)
  3. Empty-response check
"""

from __future__ import annotations

import re


class BlockDetectionResult:
    """Result of block page detection."""
    __slots__ = ("blocked", "reason")

    def __init__(self, blocked: bool, reason: str = ""):
        self.blocked = blocked
        self.reason = reason


# Engine-specific block patterns
_ENGINE_BLOCK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sorry\.google\.com|/sorry/index|/sorry/recaptcha", re.I),
     "Google CAPTCHA"),
    (re.compile(r"bing\.com/security/|bing\.com/secure/", re.I),
     "Bing block"),
    (re.compile(r"duckduckgo\.com/.*[?&]t=hc_|id\s*=\s*[\"']challenge-form[\"']", re.I),
     "DDG challenge"),
]

# Generic anti-bot patterns (only trigger on short pages < 2KB)
_GENERIC_BLOCK_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Access\s+Denied", re.I), "Access Denied"),
    (re.compile(r"Checking\s+your\s+browser", re.I), "Browser check"),
    (re.compile(r"challenge-form.*__cf_chl_f_tk=", re.I | re.S),
     "Cloudflare challenge"),
    (re.compile(r"Reference\s*#\s*[\da-f]+\.[\da-f]+", re.I),
     "Akamai block"),
    (re.compile(r"window\._pxAppId\s*=", re.I), "PerimeterX block"),
    (re.compile(r"Please\s+complete\s+the\s+security\s+check", re.I),
     "Security check"),
]

_BLOCK_PAGE_SIZE_THRESHOLD = 2048  # 2KB


def detect_block_page(html: str, url: str = "") -> BlockDetectionResult:
    """Detect if the returned HTML is a block/anti-bot page.

    Three-tier detection:
      1. Engine-specific patterns (always checked)
      2. Generic anti-bot patterns (only on short pages < 2KB)
      3. Structural integrity check (body exists, has content)
    """
    if not html:
        return BlockDetectionResult(blocked=True, reason="Empty response")

    # Tier 1: Engine-specific
    for pattern, reason in _ENGINE_BLOCK_PATTERNS:
        if pattern.search(html) or pattern.search(url):
            return BlockDetectionResult(blocked=True, reason=reason)

    # Tier 2: Generic keywords (only on short pages to avoid false positives)
    if len(html) < _BLOCK_PAGE_SIZE_THRESHOLD:
        for pattern, reason in _GENERIC_BLOCK_KEYWORDS:
            if pattern.search(html):
                return BlockDetectionResult(blocked=True, reason=reason)

    return BlockDetectionResult(blocked=False)
