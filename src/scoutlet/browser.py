"""CDP browser runner for scoutlet.

Uses Chrome DevTools Protocol (CDP) to execute search requests via a
user's existing Chrome browser session.  This bypasses anti-bot detection
since requests appear to come from a real logged-in browser.

Usage:
    1. Start Chrome with debugging port (or enable auto_launch_browser):
       chrome --remote-debugging-port=9222 --user-data-dir=/path/to/profile

    2. Configure engines to use browser fallback:
       load_engines(engine_configs={
           "google": {"fallback_to_browser": True},
       })

    3. When HTTP engine fails, scoutlet automatically retries via CDP
"""

from __future__ import annotations

import json
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
import typing as t
import urllib.request
import urllib.error

try:
    import pychrome
except ImportError:
    pychrome = None  # type: ignore[assignment]

from scoutlet.exceptions import SearchEngineCaptchaException

import logging

logger = logging.getLogger("scoutlet.browser")

# Default CDP debugging endpoint
DEFAULT_CDP_ENDPOINT = "http://localhost:9222"

# Resource types to block for faster page loads
_BLOCKED_RESOURCE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp4", ".mp3", ".wav", ".avi", ".mov", ".webm",
    ".css",
}


def _find_chrome_binary() -> str | None:
    """Find Chrome/Chromium binary on the current system."""
    system = platform.system()
    candidates: list[str] = []

    if system == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    elif system == "Linux":
        candidates = [
            "google-chrome", "google-chrome-stable",
            "chromium", "chromium-browser",
        ]
    elif system == "Windows":
        candidates = [
            os.path.expandvars(
                r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
            ),
            os.path.expandvars(
                r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
            ),
        ]

    for path in candidates:
        if os.path.isfile(path) or _is_on_path(path):
            return path
    return None


def _is_on_path(name: str) -> bool:
    try:
        from shutil import which
        return which(name) is not None
    except Exception:
        return False


def _parse_cdp_port(endpoint: str) -> int:
    """Extract port number from CDP endpoint URL."""
    try:
        from urllib.parse import urlparse
        return int(urlparse(endpoint).port or 9222)
    except Exception:
        return 9222


# ---------------------------------------------------------------------------
# Anti-bot / block page detection
# ---------------------------------------------------------------------------

# Engine-specific block patterns
_ENGINE_BLOCK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sorry\.google\.com|/sorry/index|/sorry/recaptcha", re.I),
     "Google CAPTCHA"),
    (re.compile(r"bing\.com/security/|bing\.com/secure/", re.I),
     "Bing block"),
    (re.compile(r"duckduckgo\.com/.*[?&]t=hc_", re.I),
     "DDG rate limit"),
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


class BlockDetectionResult:
    """Result of block page detection."""
    __slots__ = ("blocked", "reason")

    def __init__(self, blocked: bool, reason: str = ""):
        self.blocked = blocked
        self.reason = reason


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


# ---------------------------------------------------------------------------
# CDP endpoint verification
# ---------------------------------------------------------------------------

def verify_cdp_endpoint(endpoint: str, attempts: int = 3) -> bool:
    """Verify CDP endpoint is reachable via /json/version.

    Uses exponential backoff: 0.5s × 1.5^attempt.
    """
    from urllib.parse import urlparse, urlunparse

    if endpoint.startswith(("ws://", "wss://")):
        return True  # WebSocket URLs handled by pychrome directly

    parsed = urlparse(endpoint)
    verify_url = urlunparse((
        parsed.scheme, parsed.netloc, "/json/version", "", "", ""
    ))

    for attempt in range(attempts):
        try:
            req = urllib.request.Request(verify_url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        delay = 0.5 * (1.5 ** attempt)
        time.sleep(delay)

    return False


# ---------------------------------------------------------------------------
# Managed browser (auto-launch)
# ---------------------------------------------------------------------------

class ManagedBrowser:
    """Automatically launch and manage a Chrome browser process."""

    def __init__(
        self,
        endpoint: str = DEFAULT_CDP_ENDPOINT,
        headless: bool = True,
        browser_args: list[str] | None = None,
        user_data_dir: str | None = None,
    ):
        self.endpoint = endpoint
        self.port = _parse_cdp_port(endpoint)
        self.headless = headless
        self.browser_args = browser_args or []
        self.user_data_dir = user_data_dir or os.path.join(
            tempfile.gettempdir(), "scoutlet-chrome-profile"
        )
        self._process: subprocess.Popen | None = None

    def start(self) -> bool:
        """Launch Chrome if not already running. Returns True if started."""
        # Check if CDP endpoint is already available
        if verify_cdp_endpoint(self.endpoint, attempts=1):
            logger.info("CDP endpoint already available at %s", self.endpoint)
            return True

        chrome_bin = _find_chrome_binary()
        if not chrome_bin:
            logger.error(
                "Chrome/Chromium not found on your system.\n"
                "  Please install Google Chrome or Chromium, or start it manually:\n"
                "    chrome --remote-debugging-port=%d --user-data-dir=/tmp/chrome-profile",
                self.port,
            )
            return False

        args = self._build_args(chrome_bin)
        logger.info("Launching browser: %s", " ".join(args))

        try:
            kwargs: dict[str, t.Any] = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = (
                    subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                kwargs["start_new_session"] = True

            self._process = subprocess.Popen(args, **kwargs)

            # Wait for CDP endpoint to become ready
            if verify_cdp_endpoint(self.endpoint, attempts=5):
                logger.info("Browser started, CDP ready at %s", self.endpoint)
                return True
            else:
                logger.error("Browser started but CDP endpoint not ready")
                self.stop()
                return False

        except Exception as e:
            logger.error("Failed to launch browser: %s", e)
            return False

    def stop(self) -> None:
        """Stop the managed browser process."""
        if self._process and self._process.poll() is None:
            logger.info("Stopping managed browser (pid=%d)", self._process.pid)
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except Exception:
                pass
            self._process = None

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _build_args(self, chrome_bin: str) -> list[str]:
        args = [chrome_bin]
        args.append(f"--remote-debugging-port={self.port}")
        args.append(f"--user-data-dir={self.user_data_dir}")

        if self.headless:
            args.append("--headless=new")

        # Memory & performance flags
        args.extend([
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-domain-reliability",
            "--disable-extensions",
            "--disable-popup-blocking",
            "--disable-sync",
            "--disable-translate",
            "--metrics-recording-only",
            "--safebrowsing-disable-auto-update",
        ])

        # User-provided extra args
        args.extend(self.browser_args)
        return args


import tempfile  # noqa: E402 — needed for default user_data_dir


# ---------------------------------------------------------------------------
# BrowserRunner — CDP connection management
# ---------------------------------------------------------------------------

class BrowserRunner:
    """Manages a CDP connection to a Chrome browser session."""

    def __init__(
        self,
        endpoint: str = DEFAULT_CDP_ENDPOINT,
        tab_timeout: float = 30.0,
        block_resources: bool = True,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.tab_timeout = tab_timeout
        self.block_resources = block_resources
        self._browser: pychrome.Browser | None = None

    def connect(self) -> pychrome.Browser:
        """Connect to Chrome debugging endpoint."""
        if self._browser is None:
            self._browser = pychrome.Browser(url=self.endpoint)
        return self._browser

    def _ensure_connected(self) -> pychrome.Browser:
        """Verify existing connection is alive, reconnect if needed."""
        if self._browser is not None:
            try:
                # Lightweight health check
                self._browser.list_tab()
                return self._browser
            except Exception:
                logger.warning("CDP connection stale, reconnecting")
                self._browser = None
        return self.connect()

    def close(self) -> None:
        """Close the CDP connection."""
        if self._browser:
            try:
                tabs = self._browser.list_tab()
                for tab in tabs:
                    self._browser.close_tab(tab)
            except Exception:
                pass
            self._browser = None

    def navigate(self, url: str, timeout: float = 15.0) -> str:
        """Navigate to URL and return rendered HTML.

        Opens a new tab, loads the URL, waits for page load,
        then returns the full page HTML.
        """
        browser = self._ensure_connected()

        # Create new tab
        tab = browser.new_tab()

        try:
            tab.start()

            # Set up resource blocking if enabled
            if self.block_resources:
                self._setup_resource_blocking(tab)

            # Enable page events for load detection
            tab.call_method("Page.enable")

            # Navigate to URL via CDP
            tab.call_method("Page.navigate", url=url)

            # Wait for page load event
            self._wait_for_load(tab, timeout)

            # Get rendered HTML via Runtime.evaluate
            result = tab.call_method(
                "Runtime.evaluate",
                expression="document.documentElement.outerHTML",
                returnByValue=True,
            )
            html = result.get("result", {}).get("value", "")
            return html

        finally:
            try:
                tab.stop()
                browser.close_tab(tab)
            except Exception:
                pass

    def navigate_with_post(
        self,
        url: str,
        post_data: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 15.0,
    ) -> str:
        """Navigate using POST method (for DDG-style form submissions)."""
        browser = self._ensure_connected()
        tab = browser.new_tab()

        try:
            tab.start()

            if self.block_resources:
                self._setup_resource_blocking(tab)

            tab.call_method("Page.enable")

            if post_data:
                # Build a form submission script
                form_parts = [
                    f"name={json.dumps(k)}, value={json.dumps(v)}"
                    for k, v in post_data.items()
                ]
                form_data = "[" + ", ".join(form_parts) + "]"

                script = f"""
                (function() {{
                    let form = document.createElement('form');
                    form.action = {json.dumps(url)};
                    form.method = 'POST';
                    let data = {form_data};
                    for (let [name, value] of data) {{
                        let input = document.createElement('input');
                        input.name = name;
                        input.value = value;
                        form.appendChild(input);
                    }}
                    document.body.appendChild(form);
                    form.submit();
                }})();
                """

                base_url = url.split("?")[0]
                tab.call_method("Page.navigate", url=base_url)
                self._wait_for_load(tab, 5)
                tab.call_method("Runtime.evaluate", expression=script)
                self._wait_for_load(tab, timeout)
            else:
                tab.call_method("Page.navigate", url=url)
                self._wait_for_load(tab, timeout)

            result = tab.call_method(
                "Runtime.evaluate",
                expression="document.documentElement.outerHTML",
                returnByValue=True,
            )
            html = result.get("result", {}).get("value", "")
            return html

        finally:
            try:
                tab.stop()
                browser.close_tab(tab)
            except Exception:
                pass

    def _setup_resource_blocking(self, tab: pychrome.Tab) -> None:
        """Block unnecessary resources (images, fonts, media, CSS) via CDP."""
        tab.call_method("Network.enable")

        tab.set_listener("Network.requestWillBeSent", lambda **kwargs: None)

        # Use Fetch domain to intercept and abort unwanted requests
        try:
            tab.call_method("Fetch.enable", patterns=[
                {"urlPattern": "*", "requestStage": "Request"}
            ])

            def _on_request_paused(**kwargs):
                request_id = kwargs.get("requestId", "")
                url = kwargs.get("request", {}).get("url", "")
                if self._should_block_url(url):
                    try:
                        tab.call_method("Fetch.failRequest",
                                        requestId=request_id,
                                        reason="BlockedByClient")
                    except Exception:
                        pass
                else:
                    try:
                        tab.call_method("Fetch.continueRequest",
                                        requestId=request_id)
                    except Exception:
                        pass

            tab.set_listener("Fetch.requestPaused", _on_request_paused)
        except Exception:
            # Fetch domain might not be available in all Chrome versions
            logger.debug("Fetch.enable not available, skipping resource blocking")

    @staticmethod
    def _should_block_url(url: str) -> bool:
        """Check if a URL should be blocked based on extension."""
        # Extract path without query string
        path = url.split("?")[0].split("#")[0].lower()
        return any(path.endswith(ext) for ext in _BLOCKED_RESOURCE_EXTENSIONS)

    def _wait_for_load(self, tab: pychrome.Tab, timeout: float) -> None:
        """Wait for page to finish loading using CDP events + polling fallback."""
        loaded = threading.Event()

        def _on_load(**kwargs):
            loaded.set()

        try:
            tab.set_listener("Page.loadEventFired", _on_load)
            if loaded.wait(timeout=timeout):
                return  # Load event received
        except Exception:
            pass

        # Fallback: poll readyState
        start = time.time()
        remaining = timeout - (time.time() - start)
        while remaining > 0:
            try:
                result = tab.call_method(
                    "Runtime.evaluate",
                    expression="document.readyState",
                    returnByValue=True,
                )
                state = result.get("result", {}).get("value", "")
                if state == "complete":
                    break
            except Exception:
                pass
            time.sleep(0.3)
            remaining = timeout - (time.time() - start)

        # Brief settle for JS rendering
        time.sleep(0.3)


# ---------------------------------------------------------------------------
# Global browser runner (singleton, reused across calls)
# ---------------------------------------------------------------------------

_browser_runner: BrowserRunner | None = None
_managed_browser: ManagedBrowser | None = None
_runner_lock = threading.Lock()


def get_browser_runner(
    endpoint: str = DEFAULT_CDP_ENDPOINT,
    block_resources: bool = True,
) -> BrowserRunner:
    """Get or create the global browser runner."""
    global _browser_runner
    with _runner_lock:
        if _browser_runner is None:
            _browser_runner = BrowserRunner(
                endpoint=endpoint, block_resources=block_resources,
            )
    return _browser_runner


def close_browser_runner() -> None:
    """Close the global browser runner and managed browser."""
    global _browser_runner, _managed_browser
    with _runner_lock:
        if _browser_runner:
            _browser_runner.close()
            _browser_runner = None
        if _managed_browser:
            _managed_browser.stop()
            _managed_browser = None


def ensure_browser_ready(
    endpoint: str = DEFAULT_CDP_ENDPOINT,
    auto_launch: bool = False,
    headless: bool = True,
    browser_args: list[str] | None = None,
) -> bool:
    """Ensure a browser is available at the CDP endpoint.

    If auto_launch is True and no browser is running, starts one automatically.
    Returns True if CDP endpoint is ready.
    """
    # Already running?
    if verify_cdp_endpoint(endpoint, attempts=1):
        return True

    if not auto_launch:
        logger.error(
            "CDP endpoint %s not reachable.\n"
            "  Option 1: Start Chrome manually with:\n"
            "    chrome --remote-debugging-port=%d --user-data-dir=/tmp/chrome-profile\n"
            "  Option 2: Enable auto-launch in engine config:\n"
            "    load_engines(engine_configs={'google': {\n"
            "        'fallback_to_browser': True,\n"
            "        'auto_launch_browser': True,\n"
            "    }})",
            endpoint, _parse_cdp_port(endpoint),
        )
        return False

    global _managed_browser
    with _runner_lock:
        if _managed_browser is None or not _managed_browser.is_running:
            _managed_browser = ManagedBrowser(
                endpoint=endpoint,
                headless=headless,
                browser_args=browser_args,
            )
        if not _managed_browser.start():
            return False

    return True


def run_via_cdp(
    url: str,
    method: str = "GET",
    post_data: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    cdp_endpoint: str = DEFAULT_CDP_ENDPOINT,
    timeout: float = 15.0,
    auto_launch_browser: bool = False,
    headless: bool = True,
    browser_args: list[str] | None = None,
    block_resources: bool = True,
    _retry_headful: bool = False,
) -> tuple[str, int]:
    """Execute a request via CDP browser and return (html, status_code).

    Args:
        url: Target URL
        method: HTTP method (GET or POST)
        post_data: POST form data
        headers: Additional headers (ignored for browser mode)
        cdp_endpoint: CDP debugging endpoint
        timeout: Navigation timeout
        auto_launch_browser: Auto-start Chrome if not running
        headless: Use headless mode (auto-downgrades to headful on block)
        browser_args: Extra Chrome CLI arguments
        block_resources: Block images/fonts/CSS for speed
        _retry_headful: Internal flag for headless→headful downgrade

    Returns:
        tuple of (rendered_html, http_status_code)
    """
    # Ensure browser is available
    if not ensure_browser_ready(
        endpoint=cdp_endpoint,
        auto_launch=auto_launch_browser,
        headless=headless,
        browser_args=browser_args,
    ):
        raise SearchEngineCaptchaException(
            suspended_time=0,
            message=(
                f"CDP browser not available at {cdp_endpoint}. "
                f"Start Chrome with --remote-debugging-port={_parse_cdp_port(cdp_endpoint)} "
                f"or set auto_launch_browser=True"
            ),
        )

    # Reuse global runner
    runner = get_browser_runner(endpoint=cdp_endpoint, block_resources=block_resources)

    try:
        if method.upper() == "POST" and post_data:
            html = runner.navigate_with_post(url, post_data, headers, timeout)
        else:
            html = runner.navigate(url, timeout)

        # Detect block/anti-bot pages
        detection = detect_block_page(html, url)
        if detection.blocked:
            # If we're in headless and haven't retried headful yet, downgrade
            if headless and not _retry_headful and auto_launch_browser:
                logger.warning(
                    "Headless blocked (%s), retrying with headful",
                    detection.reason,
                )
                # Restart browser in headful mode
                close_browser_runner()
                global _managed_browser
                _managed_browser = ManagedBrowser(
                    endpoint=cdp_endpoint,
                    headless=False,
                    browser_args=browser_args,
                )
                if _managed_browser.start():
                    return run_via_cdp(
                        url=url,
                        method=method,
                        post_data=post_data,
                        headers=headers,
                        cdp_endpoint=cdp_endpoint,
                        timeout=timeout,
                        auto_launch_browser=True,
                        headless=False,
                        browser_args=browser_args,
                        block_resources=block_resources,
                        _retry_headful=True,
                    )

            status = 403
        else:
            status = 200

        return html, status

    except Exception as e:
        logger.error("CDP navigation failed: %s", e)
        raise SearchEngineCaptchaException(
            suspended_time=0,
            message=f"CDP browser error: {e}",
        )
