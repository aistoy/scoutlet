"""CLI entry point for scoutlet."""

import argparse
import json
import sys

from scoutlet.search import search_sync
from scoutlet.engine_loader import (
    list_available_engines,
    load_engines,
    categories,
    get_failed_engines,
)


def _print_engines_by_category(engine_dir):
    """Load all engines and print them grouped by category."""
    load_engines(engine_dir=engine_dir)
    if not categories:
        print("No engines found. Add engine .py files to the engines/ directory.")
        return
    total = len({e.name for engines in categories.values() for e in engines})
    print(f"{total} engines in {len(categories)} categories:")
    print()
    for cat in sorted(categories):
        names = sorted({e.name for e in categories[cat]})
        print(f"{cat} ({len(names)}):")
        for name in names:
            print(f"  {name}")
        print()

    failed = get_failed_engines()
    if failed:
        print(f"failed to load ({len(failed)}):")
        for name, reason in sorted(failed.items()):
            print(f"  {name}  - {reason}")
        print()


def main():
    parser = argparse.ArgumentParser(
        prog="scoutlet",
        description="Minimal local search aggregator",
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument(
        "--engines", "-e",
        default=None,
        help="Comma-separated engine names (overrides --categories)",
    )
    parser.add_argument(
        "--categories", "-c",
        default=None,
        help="Comma-separated categories (default: general)",
    )
    parser.add_argument(
        "--language", "-l",
        default="all",
        help="Language code (default: all)",
    )
    parser.add_argument(
        "--time-range", "-t",
        default=None,
        choices=["day", "week", "month", "year"],
        help="Time range filter",
    )
    parser.add_argument(
        "--page", "-p",
        type=int,
        default=1,
        help="Page number (default: 1)",
    )
    parser.add_argument(
        "--safesearch", "-s",
        type=int,
        default=0,
        choices=[0, 1, 2],
        help="Safe search level (default: 0)",
    )
    parser.add_argument(
        "--format", "-f",
        default="text",
        choices=["text", "json"],
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-engine timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--engine-dir",
        default=None,
        help="Custom engine directory path",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="HTTP/SOCKS5 proxy URL (e.g., socks5://127.0.0.1:1080)",
    )
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="List available engines and exit",
    )
    parser.add_argument(
        "--by-category",
        action="store_true",
        help="With --list-engines, group engines by category",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch local web UI (browser-based search interface)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Web UI bind host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5123,
        help="Web UI port (default: 5123; auto-bumps if taken)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="With --ui, don't auto-open the browser",
    )
    parser.add_argument(
        "--adapter-backend",
        choices=["httpx", "default", "fingerprint"],
        default=None,
        help="HTTP client backend (default: httpx). 'fingerprint' uses primp with "
             "browser TLS impersonation to bypass Cloudflare-style blocks; install "
             "with: uv sync --extra fingerprint",
    )

    args = parser.parse_args()

    if args.ui:
        from scoutlet.webui import run_server
        run_server(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
        )
        return

    if args.list_engines:
        if args.by_category:
            _print_engines_by_category(args.engine_dir)
        else:
            engine_names = list_available_engines(args.engine_dir)
            if not engine_names:
                print("No engines found. Add engine .py files to the engines/ directory.")
                sys.exit(1)
            for name in engine_names:
                print(name)
        return

    if not args.query:
        parser.error("query is required (unless --list-engines)")

    engines_list = args.engines.split(",") if args.engines else None
    categories_list = args.categories.split(",") if args.categories else None

    try:
        results = search_sync(
            query=args.query,
            engines=engines_list,
            categories=categories_list,
            language=args.language,
            time_range=args.time_range,
            pageno=args.page,
            safesearch=args.safesearch,
            timeout=args.timeout,
            engine_dir=args.engine_dir,
            proxy=args.proxy,
            search_adapter_backend=args.adapter_backend,
        )
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        output = [r.as_dict() for r in results]
        json.dump(output, sys.stdout, indent=2, default=str, ensure_ascii=False)
        print()  # trailing newline
    else:
        if not results:
            print("No results found.")
            return
        for i, r in enumerate(results, 1):
            engines_str = ",".join(sorted(r.engines)) if r.engines else r.engine
            print(f"{i}. [{engines_str}] {r.title}")
            print(f"   {r.url}")
            if r.content:
                content = r.content[:150]
                if len(r.content) > 150:
                    content += "..."
                print(f"   {content}")
            if r.score:
                print(f"   score: {r.score:.2f}")
            print()


if __name__ == "__main__":
    main()
