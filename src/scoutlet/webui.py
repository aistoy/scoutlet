"""Minimal local web UI for scoutlet.

Runs on Python's built-in http.server — no extra dependencies. Serves an HTML
search page styled after ui-demo.html and exposes two JSON endpoints:

  GET /api/engines   -> {categories: [...], engines: [...]}
  GET /api/search    -> {query, count, results: [...]}

Use ``scoutlet --ui`` to launch; the default browser opens automatically.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import threading
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import logging

log = logging.getLogger("scoutlet.webui")

TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5123


def _load_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def _engine_summary() -> dict:
    """Build {categories, engines, engines_by_category} without setup() calls.

    Uses peek_engine_categories so spotify/youtube_api and friends don't emit
    setup noise or take network round-trips at UI startup. The category→engines
    mapping lets the UI narrow the engine list when one or more categories are
    selected.
    """
    from scoutlet.engine_loader import list_available_engines, peek_engine_categories

    cats: set[str] = set()
    engines = list_available_engines()
    by_cat: dict[str, list[str]] = {}
    for name in engines:
        eng_cats = peek_engine_categories(name)
        for c in eng_cats:
            cats.add(c)
            by_cat.setdefault(c, []).append(name)
    return {
        "categories": sorted(cats),
        "engines": sorted(engines),
        "engines_by_category": {c: sorted(names) for c, names in by_cat.items()},
    }


def _parse_search_params(qs: dict[str, list[str]]) -> dict:
    def first(key: str, default: str = "") -> str:
        v = qs.get(key, [default])
        return v[0] if v else default

    engines_raw = first("engines")
    category_raw = first("category")
    return {
        "query": first("q").strip(),
        "engines": [e for e in engines_raw.split(",") if e] or None,
        "categories": [c for c in category_raw.split(",") if c] or None,
        "language": first("language", "all") or "all",
        "time_range": first("time_range") or None,
        "pageno": max(1, int(first("page", "1") or "1")),
        "timeout": float(first("timeout", "10") or "10"),
    }


def _do_search(params: dict) -> dict:
    from scoutlet.search import search_sync

    if not params["query"]:
        return {"error": "empty query", "results": [], "count": 0}

    results = search_sync(
        query=params["query"],
        engines=params["engines"],
        categories=params["categories"],
        pageno=params["pageno"],
        language=params["language"],
        time_range=params["time_range"],
        timeout=params["timeout"],
    )
    return {
        "query": params["query"],
        "count": len(results),
        "results": [r.as_dict() for r in results],
    }


class ScoutletHandler(http.server.BaseHTTPRequestHandler):
    server_version = "scoutlet-ui/0.1"

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self._send(body, "application/json; charset=utf-8", status)

    def _send_html(self, body: str, status: int = 200) -> None:
        self._send(body.encode("utf-8"), "text/html; charset=utf-8", status)

    def do_GET(self) -> None:  # noqa: N802 (http.server convention)
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query, keep_blank_values=True)

        if path in ("/", "/index.html"):
            try:
                self._send_html(_load_template())
            except FileNotFoundError:
                self._send_html(
                    "<h1>scoutlet UI template missing</h1>", status=500,
                )
            return

        if path == "/api/engines":
            try:
                self._send_json(_engine_summary())
            except Exception as e:
                log.exception("engine summary failed")
                self._send_json({"error": str(e)}, status=500)
            return

        if path == "/api/search":
            try:
                params = _parse_search_params(qs)
                self._send_json(_do_search(params))
            except Exception as e:
                log.exception("search failed")
                self._send_json({"error": str(e), "results": [], "count": 0}, status=500)
            return

        self._send(b"Not Found", "text/plain; charset=utf-8", status=404)

    def log_message(self, fmt: str, *args) -> None:
        # Quiet by default; flip on by setting level=logging.INFO.
        if log.isEnabledFor(logging.INFO):
            super().log_message(fmt, *args)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _pick_free_port(host: str, start: int, attempts: int = 20) -> int:
    """Return ``start`` if it's free, else walk upward until we find one.

    Stops after ``attempts`` tries and returns the last tried port (caller will
    get the bind error and surface it).
    """
    import socket

    port = start
    for _ in range(attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                port += 1
    return start


def run_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    open_browser: bool = True,
    auto_port: bool = True,
) -> None:
    """Serve the scoutlet UI until interrupted.

    Args:
        host: Bind address (default 127.0.0.1 — local only).
        port: Preferred port; bumped automatically if occupied when auto_port.
        open_browser: Open the default browser to the page on start.
        auto_port: If the preferred port is taken, try the next ones up.
    """
    actual_port = _pick_free_port(host, port) if auto_port else port
    server = ThreadingHTTPServer((host, actual_port), ScoutletHandler)
    url = f"http://{host}:{actual_port}/"

    lines = [
        "",
        "  ScoutLet UI",
        f"  listening:  {url}",
        f"  engines:    run a search to load (peek-only at startup)",
        "  stop:       Ctrl+C",
        "",
    ]
    print("\n".join(lines), flush=True)

    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.shutdown()
        server.server_close()
