"""CDP fallback mock tests — verify headless→headful retry flow and browser readiness.

These tests mock pychrome/CDP layer and never launch a real browser.
"""

from unittest.mock import patch, MagicMock

import pytest

from scoutlet.browser import (
    _build_blocked_url_patterns,
    _build_post_form_script,
    _default_user_data_dir,
    detect_block_page,
    ensure_browser_ready,
    ManagedBrowser,
    resolve_cdp_endpoint_for_launch,
    run_via_cdp,
    close_browser_runner,
    _managed_browser as _managed_browser_module,
)
from scoutlet.exceptions import SearchEngineCaptchaException


@pytest.fixture(autouse=True)
def cleanup_globals():
    """Reset global browser state between tests."""
    close_browser_runner()
    yield
    close_browser_runner()


class TestEnsureBrowserReady:
    @patch("scoutlet.browser.verify_cdp_endpoint", return_value=True)
    def test_returns_true_when_endpoint_available(self, mock_verify):
        assert ensure_browser_ready("http://localhost:9222") is True
        mock_verify.assert_called_once()

    @patch("scoutlet.browser.verify_cdp_endpoint", return_value=False)
    def test_returns_false_when_no_auto_launch(self, mock_verify):
        assert ensure_browser_ready("http://localhost:9222", auto_launch=False) is False

    @patch("scoutlet.browser.verify_cdp_endpoint", return_value=False)
    @patch("scoutlet.browser.ManagedBrowser")
    def test_auto_launch_starts_browser(self, MockBrowser, mock_verify):
        mock_instance = MagicMock()
        mock_instance.start.return_value = True
        MockBrowser.return_value = mock_instance

        assert ensure_browser_ready("http://localhost:9222", auto_launch=True) is True
        MockBrowser.assert_called_once()
        mock_instance.start.assert_called_once()

    @patch("scoutlet.browser.verify_cdp_endpoint", return_value=False)
    @patch("scoutlet.browser.ManagedBrowser")
    def test_auto_launch_fails_returns_false(self, MockBrowser, mock_verify):
        mock_instance = MagicMock()
        mock_instance.start.return_value = False
        MockBrowser.return_value = mock_instance

        assert ensure_browser_ready("http://localhost:9222", auto_launch=True) is False

    @patch("scoutlet.browser.verify_cdp_endpoint", return_value=True)
    @patch("scoutlet.browser.cdp_endpoint_is_headless", return_value=True)
    @patch("scoutlet.browser._find_free_cdp_endpoint", return_value="http://localhost:9333")
    def test_headful_auto_launch_avoids_existing_headless_endpoint(
        self,
        mock_free_endpoint,
        mock_is_headless,
        mock_verify,
    ):
        endpoint = resolve_cdp_endpoint_for_launch(
            "http://localhost:9222",
            auto_launch=True,
            headless=False,
        )

        assert endpoint == "http://localhost:9333"
        mock_free_endpoint.assert_called_once_with("http://localhost:9222")

    @patch("scoutlet.browser.verify_cdp_endpoint")
    def test_headless_auto_launch_keeps_requested_endpoint(self, mock_verify):
        endpoint = resolve_cdp_endpoint_for_launch(
            "http://localhost:9222",
            auto_launch=True,
            headless=True,
        )

        assert endpoint == "http://localhost:9222"
        mock_verify.assert_not_called()

    def test_managed_browser_default_profile_is_port_scoped(self):
        browser_9222 = ManagedBrowser(endpoint="http://localhost:9222")
        browser_9333 = ManagedBrowser(endpoint="http://localhost:9333")

        assert browser_9222.user_data_dir == _default_user_data_dir(
            "http://localhost:9222"
        )
        assert browser_9333.user_data_dir == _default_user_data_dir(
            "http://localhost:9333"
        )
        assert browser_9222.user_data_dir != browser_9333.user_data_dir
        assert browser_9222.user_data_dir.endswith("scoutlet-chrome-profile-9222")
        assert browser_9333.user_data_dir.endswith("scoutlet-chrome-profile-9333")


class TestRunViaCdp:
    @patch("scoutlet.browser.ensure_browser_ready", return_value=True)
    @patch("scoutlet.browser.get_browser_runner")
    def test_normal_page_returns_200(self, mock_get_runner, mock_ready):
        mock_runner = MagicMock()
        mock_runner.navigate.return_value = "<html><body>Normal page content</body></html>"
        mock_get_runner.return_value = mock_runner

        html, status = run_via_cdp(url="https://example.com")
        assert status == 200
        assert "Normal page" in html

    @patch("scoutlet.browser.resolve_cdp_endpoint_for_launch",
           return_value="http://localhost:9333")
    @patch("scoutlet.browser.ensure_browser_ready", return_value=True)
    @patch("scoutlet.browser.get_browser_runner")
    def test_uses_resolved_endpoint(self, mock_get_runner, mock_ready, mock_resolve):
        mock_runner = MagicMock()
        mock_runner.navigate.return_value = "<html><body>Normal page content</body></html>"
        mock_get_runner.return_value = mock_runner

        html, status = run_via_cdp(
            url="https://example.com",
            cdp_endpoint="http://localhost:9222",
            auto_launch_browser=True,
            headless=False,
        )

        assert status == 200
        assert "Normal page" in html
        mock_ready.assert_called_once()
        assert mock_ready.call_args.kwargs["endpoint"] == "http://localhost:9333"
        mock_get_runner.assert_called_once_with(
            endpoint="http://localhost:9333",
            block_resources=True,
        )

    @patch("scoutlet.browser.ensure_browser_ready", return_value=True)
    @patch("scoutlet.browser.get_browser_runner")
    def test_blocked_page_returns_403(self, mock_get_runner, mock_ready):
        mock_runner = MagicMock()
        mock_runner.navigate.return_value = '<html><body>sorry.google.com recaptcha</body></html>'
        mock_get_runner.return_value = mock_runner

        html, status = run_via_cdp(
            url="https://www.google.com/sorry/index",
            headless=False,
            _retry_headful=True,
        )
        assert status == 403

    @patch("scoutlet.browser.ensure_browser_ready", return_value=False)
    def test_no_browser_raises_captcha(self, mock_ready):
        with pytest.raises(SearchEngineCaptchaException, match="CDP browser not available"):
            run_via_cdp(url="https://example.com")

    @patch("scoutlet.browser.ensure_browser_ready", return_value=True)
    @patch("scoutlet.browser.get_browser_runner")
    def test_headless_blocked_retries_headful(self, mock_get_runner, mock_ready):
        call_count = 0

        def mock_navigate(url, timeout=15.0):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: headless returns blocked page
                return '<html><body>Access Denied</body></html>'
            # Second call: headful returns normal page
            return '<html><body>Real search results</body></html>'

        mock_runner = MagicMock()
        mock_runner.navigate.side_effect = mock_navigate
        mock_get_runner.return_value = mock_runner

        with patch("scoutlet.browser.ManagedBrowser") as MockBrowser:
            mock_browser = MagicMock()
            mock_browser.start.return_value = True
            MockBrowser.return_value = mock_browser

            html, status = run_via_cdp(
                url="https://example.com",
                auto_launch_browser=True,
                headless=True,
            )
            # Should eventually get 200 from headful retry
            assert status == 200
            assert "Real search results" in html
            assert call_count == 2

    @patch("scoutlet.browser.ensure_browser_ready", return_value=True)
    @patch("scoutlet.browser.get_browser_runner")
    def test_headful_retry_only_once(self, mock_get_runner, mock_ready):
        """Headless blocked + headful also blocked → 403, no infinite loop."""
        mock_runner = MagicMock()
        mock_runner.navigate.return_value = '<html><body>Access Denied</body></html>'
        mock_get_runner.return_value = mock_runner

        with patch("scoutlet.browser.ManagedBrowser") as MockBrowser:
            mock_browser = MagicMock()
            mock_browser.start.return_value = True
            MockBrowser.return_value = mock_browser

            html, status = run_via_cdp(
                url="https://example.com",
                auto_launch_browser=True,
                headless=True,
            )
            assert status == 403
            assert mock_runner.navigate.call_count == 2  # headless + headful, then stop

    @patch("scoutlet.browser.ensure_browser_ready", return_value=True)
    @patch("scoutlet.browser.get_browser_runner")
    def test_post_method_uses_navigate_with_post(self, mock_get_runner, mock_ready):
        mock_runner = MagicMock()
        mock_runner.navigate_with_post.return_value = "<html><body>Result</body></html>"
        mock_get_runner.return_value = mock_runner

        html, status = run_via_cdp(
            url="https://example.com",
            method="POST",
            post_data={"q": "test"},
        )
        assert status == 200
        mock_runner.navigate_with_post.assert_called_once()
        mock_runner.navigate.assert_not_called()

    def test_post_form_script_uses_name_value_pairs(self):
        script = _build_post_form_script(
            "https://html.duckduckgo.com/html/",
            {"q": "python asyncio", "s": None},
        )

        assert '[["q", "python asyncio"], ["s", ""]]' in script
        assert "for (let [name, value] of data)" in script
        assert "name=\"q\"" not in script

    def test_blocked_url_patterns_include_query_variants(self):
        patterns = _build_blocked_url_patterns()

        assert "*.css" in patterns
        assert "*.css?*" in patterns
        assert "*.png#*" in patterns

    @patch("scoutlet.browser.ensure_browser_ready", return_value=True)
    @patch("scoutlet.browser.get_browser_runner")
    def test_navigation_exception_raises_captcha(self, mock_get_runner, mock_ready):
        mock_runner = MagicMock()
        mock_runner.navigate.side_effect = RuntimeError("Tab crashed")
        mock_get_runner.return_value = mock_runner

        with pytest.raises(SearchEngineCaptchaException, match="CDP browser error"):
            run_via_cdp(url="https://example.com")
