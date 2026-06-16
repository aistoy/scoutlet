#!/usr/bin/env python
"""Engine health check for scoutlet.

Runs a single search query against specified engines and outputs a JSON health report.
Each engine is classified as: healthy | empty | anti_bot | http_error | parser_error | timeout.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py -e google,bing,duckduckgo
    python scripts/health_check.py -q "test query" --output report.json
"""

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone

from scoutlet.exceptions import (
    SearchEngineAccessDeniedException,
    SearchEngineCaptchaException,
    SearchEngineTooManyRequestsException,
    SearchEngineAPIException,
    SearchEngineResponseException,
)
from scoutlet.engine_loader import load_engine, load_engines, list_available_engines


DEFAULT_QUERY = "python tutorial"
DEFAULT_ENGINES = ["bing", "google", "duckduckgo", "qwant", "baidu", "brave", "sogou"]

_SNAPSHOT_STATUS_MAP = {"healthy": "success", "empty": "failed", "parser_error": "failed"}


def check_engine(
    engine_name: str,
    query: str,
    timeout: float = 10.0,
    snapshots_dir: str | None = None,
) -> dict:
    """Run a single search against one engine and return a health report entry."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine": engine_name,
        "query": query,
        "status": "unknown",
        "result_count": 0,
        "response_time_ms": 0,
        "error": None,
    }

    engine = load_engine(engine_name)
    if engine is None:
        entry["status"] = "load_error"
        entry["error"] = f"Engine module not found: {engine_name}"
        return entry

    resp_text = None

    try:
        # Build params — match _build_default_params in search.py so health
        # check uses the same header set as actual search runs. A hardcoded
        # UA previously triggered Bing's anti-bot and made the engine look
        # broken even though search_sync worked fine.
        from scoutlet.utils import gen_useragent
        params = {
            "method": "GET",
            "headers": {
                "User-Agent": gen_useragent(),
                "Accept-Language": "en,en-US;q=0.7,en;q=0.3",
                "Accept-Encoding": "gzip, deflate",
                "Cache-Control": "no-cache",
                "DNT": "1",
                "Connection": "keep-alive",
            },
            "data": {},
            "json": {},
            "url": "",
            "cookies": {},
            "auth": None,
            "allow_redirects": True,
            "query": query,
            "pageno": 1,
            "language": "all",
            "searxng_locale": "all",
            "time_range": "",
            "safesearch": 0,
            "timeout": timeout,
            "proxy": None,
            "engine_data": {},
            "raise_for_httperror": False,
        }

        # Engine builds request
        result = engine.request(query, params)
        if result is not None:
            params = result

        if not params.get("url"):
            entry["status"] = "empty"
            entry["error"] = "Engine returned no URL"
            return entry

        # Send HTTP request
        from scoutlet import network

        start = time.monotonic()
        method = params.get("method", "GET").upper()
        kwargs = {
            "headers": params.get("headers", {}),
            "cookies": params.get("cookies", {}),
            "timeout": params.get("timeout", timeout),
            "proxy": params.get("proxy"),
            "follow_redirects": params.get("allow_redirects", True),
        }

        if method == "POST":
            data = params.get("data")
            json_data = params.get("json")
            if data:
                kwargs["data"] = data
            if json_data:
                kwargs["json"] = json_data
            resp = network.post(params["url"], **kwargs)
        else:
            resp = network.get(params["url"], **kwargs)

        resp_text = getattr(resp, "text", None)
        elapsed_ms = round((time.monotonic() - start) * 1000)
        entry["response_time_ms"] = elapsed_ms

        # Check HTTP errors
        if resp.status_code in (403, 503):
            entry["status"] = "anti_bot"
            entry["error"] = f"HTTP {resp.status_code}"
            return entry
        if resp.status_code == 429:
            entry["status"] = "anti_bot"
            entry["error"] = "HTTP 429 Too Many Requests"
            return entry
        if resp.status_code >= 400:
            entry["status"] = "http_error"
            entry["error"] = f"HTTP {resp.status_code}"
            return entry

        # Parse response
        resp.search_params = params
        results = engine.response(resp)
        count = len([r for r in results if isinstance(r, dict) and r.get("url")])
        entry["result_count"] = count

        if count > 0:
            entry["status"] = "healthy"
        else:
            entry["status"] = "empty"
            entry["error"] = "HTTP 200 but no results parsed"

    except (SearchEngineCaptchaException, SearchEngineAccessDeniedException, SearchEngineTooManyRequestsException) as e:
        entry["status"] = "anti_bot"
        entry["error"] = type(e).__name__
    except SearchEngineAPIException as e:
        entry["status"] = "http_error"
        entry["error"] = str(e)
    except SearchEngineResponseException as e:
        entry["status"] = "parser_error"
        entry["error"] = str(e)
    except TimeoutError as e:
        entry["status"] = "timeout"
        entry["error"] = str(e)
    except Exception as e:
        entry["status"] = "error"
        entry["error"] = f"{type(e).__name__}: {e}"
        entry["traceback"] = traceback.format_exc()

    # Save HTML snapshot
    if snapshots_dir and resp_text:
        snap_status = _SNAPSHOT_STATUS_MAP.get(entry["status"])
        if snap_status:
            try:
                from pathlib import Path
                from snapshot import save_snapshot
                path = save_snapshot(
                    engine_name, resp_text, snap_status, Path(snapshots_dir)
                )
                entry["snapshot_path"] = str(path)
            except Exception as e:
                entry["snapshot_error"] = str(e)

    return entry


def main():
    parser = argparse.ArgumentParser(description="scoutlet engine health check")
    parser.add_argument("-e", "--engines", default=None, help="Comma-separated engine names (default: P0 engines)")
    parser.add_argument("-q", "--query", default=DEFAULT_QUERY, help=f"Search query (default: {DEFAULT_QUERY})")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-engine timeout in seconds")
    parser.add_argument("--output", "-o", default=None, help="Write report to file instead of stdout")
    parser.add_argument("--all", action="store_true", help="Check all available engines")
    parser.add_argument("--snapshots-dir", default=None, help="Save HTML snapshots to this directory")
    args = parser.parse_args()

    if args.all:
        engine_names = list_available_engines()
    elif args.engines:
        engine_names = [e.strip() for e in args.engines.split(",")]
    else:
        engine_names = DEFAULT_ENGINES

    print(f"Checking {len(engine_names)} engines with query: {args.query!r}", file=sys.stderr)

    report = []
    for name in engine_names:
        print(f"  {name} ...", end=" ", file=sys.stderr)
        entry = check_engine(name, args.query, timeout=args.timeout, snapshots_dir=args.snapshots_dir)
        report.append(entry)
        print(entry["status"], file=sys.stderr)

    output = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print(f"\nReport written to {args.output}", file=sys.stderr)
    else:
        print(output)

    # Print summary
    from collections import Counter
    statuses = Counter(e["status"] for e in report)
    print(f"\nSummary: {dict(statuses)}", file=sys.stderr)

    # Exit code: non-zero if all engines failed
    healthy = statuses.get("healthy", 0)
    if healthy == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
