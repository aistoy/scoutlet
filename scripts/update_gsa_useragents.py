#!/usr/bin/env python
"""Fetch user agents suitable for Google search.

Downloads Android Chrome user agents from https://github.com/intoli/user-agents/
and writes them to scoutlet/data/gsa_useragents.txt.

Usage:
    python scripts/update_gsa_useragents.py
    python scripts/update_gsa_useragents.py --dry-run
    python scripts/update_gsa_useragents.py --output /tmp/gsa_useragents.txt

Adapted from SearXNG's searxng_extra/update/update_gsa_useragents.py.
"""

import argparse
import sys
from gzip import decompress
from json import loads
from pathlib import Path

try:
    import httpx
except ImportError:
    import urllib.request
    httpx = None

DATA_FILE = Path(__file__).parent.parent / "src" / "scoutlet" / "data" / "gsa_useragents.txt"
URL = "https://raw.githubusercontent.com/intoli/user-agents/main/src/user-agents.json.gz"


def fetch_gsa_useragents() -> list[str]:
    """Fetch Android Chrome user agents from intoli/user-agents repo."""
    if httpx:
        response = httpx.get(URL, timeout=10.0)
        response.raise_for_status()
        raw = response.content
    else:
        req = urllib.request.Request(URL)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()

    suas: set[str] = set()
    for ua in loads(decompress(raw)):
        if (
            "Android" in ua["userAgent"]
            and "Chrome" in ua["userAgent"]
            and "Samsung" not in ua["userAgent"]
            and "Android 10; K" not in ua["userAgent"]
        ):
            suas.add(ua["userAgent"])

    return sorted(suas)


def main():
    parser = argparse.ArgumentParser(description="Update GSA user agents for Google search")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print user agents without writing to file",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output file path (default: src/scoutlet/data/gsa_useragents.txt)",
    )
    args = parser.parse_args()

    print(f"Fetching user agents from {URL} ...")
    useragents = fetch_gsa_useragents()

    if args.dry_run:
        print(f"Found {len(useragents)} user agents (dry-run, not written):")
        for ua in useragents[:10]:
            print(f"  {ua}")
        if len(useragents) > 10:
            print(f"  ... and {len(useragents) - 10} more")
        # Verify each line contains Android + Chrome
        for ua in useragents:
            assert "Android" in ua and "Chrome" in ua, f"Invalid UA: {ua}"
        print("Validation passed: all UAs contain Android + Chrome")
        return

    output_path = Path(args.output) if args.output else DATA_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(useragents))
    print(f"Wrote {len(useragents)} user agents to {output_path}")


if __name__ == "__main__":
    main()
