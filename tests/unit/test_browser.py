"""Unit tests for browser anti-bot detection."""

import pytest

from scoutlet.browser import detect_block_page, BlockDetectionResult


class TestDetectBlockPage:
    # --- Engine-specific detection ---

    def test_google_sorry_detected(self):
        html = '<html><body>sorry.google.com recaptcha</body></html>'
        result = detect_block_page(html, "https://www.google.com/sorry/index")
        assert result.blocked is True
        assert "Google CAPTCHA" in result.reason

    def test_bing_block_detected(self):
        html = '<html><body>bing.com/security/ blocked</body></html>'
        result = detect_block_page(html)
        assert result.blocked is True
        assert "Bing block" in result.reason

    def test_ddg_rate_limit_detected(self):
        html = '<html><body>duckduckgo.com/?q=test&t=hc_abc</body></html>'
        result = detect_block_page(html)
        assert result.blocked is True
        assert "DDG" in result.reason

    def test_ddg_challenge_form_detected(self):
        html = '<html><body><form id="challenge-form"></form></body></html>'
        result = detect_block_page(html)
        assert result.blocked is True
        assert "DDG" in result.reason

    # --- Generic detection (short pages only) ---

    def test_access_denied_on_short_page(self):
        html = "<html><body>Access Denied</body></html>"
        assert len(html) < 2048
        result = detect_block_page(html)
        assert result.blocked is True
        assert "Access Denied" in result.reason

    def test_browser_check_on_short_page(self):
        html = "<html><body>Checking your browser</body></html>"
        result = detect_block_page(html)
        assert result.blocked is True

    def test_cloudflare_challenge_on_short_page(self):
        html = '<html><body><form class="challenge-form"><input name="__cf_chl_f_tk=abc"></form></body></html>'
        result = detect_block_page(html)
        assert result.blocked is True
        assert "Cloudflare" in result.reason

    def test_akamai_reference_on_short_page(self):
        html = "<html><body>Reference #123456.7890ab</body></html>"
        result = detect_block_page(html)
        assert result.blocked is True

    # --- No false positives ---

    def test_normal_page_not_blocked(self):
        html = "<html><body><h1>Python Tutorial</h1><p>Learn Python</p></body></html>"
        result = detect_block_page(html)
        assert result.blocked is False

    def test_normal_long_page_not_blocked(self):
        # "Access Denied" in a long page should NOT trigger generic detection
        html = "<html><body>" + "Normal content. " * 200 + "Access Denied" + "</body></html>"
        assert len(html) >= 2048
        result = detect_block_page(html)
        assert result.blocked is False

    def test_empty_response_blocked(self):
        result = detect_block_page("")
        assert result.blocked is True
        assert "Empty" in result.reason
