#!/usr/bin/env python
"""HTML Snapshot Manager for scoutlet auto-heal.

Saves engine HTML responses on success (baseline) and failure.
Baseline HTML is used by the AI repair agent to compare with failed HTML.

Usage:
    python scripts/snapshot.py save <engine> <html_file> --status failed
    python scripts/snapshot.py save <engine> <html_file> --status success
    python scripts/snapshot.py list [--snapshots-dir snapshots]
    python scripts/snapshot.py show <engine> [--snapshots-dir snapshots]
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from lxml import html as lxml_html


SNAPSHOTS_DIR = Path("snapshots")


def minimize_html(raw_html: str) -> str:
    """Strip scripts, styles, and large inline data to keep snapshots small."""
    try:
        doc = lxml_html.fromstring(raw_html)
    except Exception:
        return raw_html

    # remove <script>, <style>, <svg> elements
    for tag in ("script", "style", "svg", "noscript"):
        for el in doc.xpath(f"//{tag}"):
            el.getparent().remove(el)

    # remove inline event handlers
    for el in doc.xpath("//*[@onclick or @onload or @onerror]"):
        for attr in ("onclick", "onload", "onerror"):
            el.attrib.pop(attr, None)

    result = lxml_html.tostring(doc, encoding="unicode", pretty_print=True)

    # collapse excessive whitespace
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def save_snapshot(
    engine_name: str,
    html_content: str,
    status: str,
    snapshots_dir: Path = SNAPSHOTS_DIR,
) -> Path:
    """Save an HTML snapshot for an engine.

    Args:
        engine_name: Engine module name (e.g. "bing")
        html_content: Raw HTML response text
        status: "success" or "failed"
        snapshots_dir: Root directory for snapshots

    Returns:
        Path to the saved snapshot file
    """
    engine_dir = snapshots_dir / engine_name
    engine_dir.mkdir(parents=True, exist_ok=True)

    content = minimize_html(html_content)

    if status == "success":
        path = engine_dir / "baseline.html"
        path.write_text(content, encoding="utf-8")
        return path

    # failed: save with timestamp
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    path = engine_dir / f"failed_{ts}.html"
    path.write_text(content, encoding="utf-8")
    return path


def load_baseline(
    engine_name: str, snapshots_dir: Path = SNAPSHOTS_DIR
) -> str | None:
    """Load the baseline (last successful) HTML for an engine."""
    path = snapshots_dir / engine_name / "baseline.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def load_latest_failure(
    engine_name: str, snapshots_dir: Path = SNAPSHOTS_DIR
) -> tuple[str | None, Path | None]:
    """Load the most recent failure snapshot for an engine.

    Returns:
        (html_content, path) or (None, None) if no failure found
    """
    engine_dir = snapshots_dir / engine_name
    if not engine_dir.exists():
        return None, None

    failed_files = sorted(engine_dir.glob("failed_*.html"), reverse=True)
    if not failed_files:
        return None, None

    path = failed_files[0]
    return path.read_text(encoding="utf-8"), path


def list_snapshots(snapshots_dir: Path = SNAPSHOTS_DIR) -> list[dict]:
    """List all engine snapshots with their files."""
    if not snapshots_dir.exists():
        return []

    entries = []
    for engine_dir in sorted(snapshots_dir.iterdir()):
        if not engine_dir.is_dir():
            continue
        files = {}
        for f in sorted(engine_dir.iterdir()):
            if f.name == "baseline.html":
                size = f.stat().st_size
                files["baseline"] = f"{size:,} bytes"
            elif f.name.startswith("failed_"):
                files.setdefault("failures", [])
                size = f.stat().st_size
                files["failures"].append(f"{f.name} ({size:,} bytes)")
        if files:
            entries.append({"engine": engine_dir.name, "files": files})
    return entries


def main():
    parser = argparse.ArgumentParser(description="scoutlet snapshot manager")
    parser.add_argument(
        "--snapshots-dir",
        type=Path,
        default=SNAPSHOTS_DIR,
        help="Root directory for snapshots",
    )
    sub = parser.add_subparsers(dest="command")

    # save
    save_p = sub.add_parser("save", help="Save an HTML snapshot")
    save_p.add_argument("engine", help="Engine name")
    save_p.add_argument("html_file", help="Path to HTML file to save")
    save_p.add_argument(
        "--status",
        choices=["success", "failed"],
        required=True,
        help="Whether this is a success (baseline) or failure snapshot",
    )

    # list
    sub.add_parser("list", help="List all snapshots")

    # show
    show_p = sub.add_parser("show", help="Show snapshot info for an engine")
    show_p.add_argument("engine", help="Engine name")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "save":
        html_content = Path(args.html_file).read_text(encoding="utf-8")
        path = save_snapshot(args.engine, html_content, args.status, args.snapshots_dir)
        print(f"Saved {args.status} snapshot: {path}")

    elif args.command == "list":
        entries = list_snapshots(args.snapshots_dir)
        if not entries:
            print("No snapshots found.")
        for entry in entries:
            print(f"\n{entry['engine']}/")
            if "baseline" in entry["files"]:
                print(f"  baseline.html — {entry['files']['baseline']}")
            if "failures" in entry["files"]:
                print(f"  failures:")
                for f in entry["files"]["failures"]:
                    print(f"    {f}")

    elif args.command == "show":
        baseline = load_baseline(args.engine, args.snapshots_dir)
        failed_html, failed_path = load_latest_failure(
            args.engine, args.snapshots_dir
        )
        if baseline:
            print(f"Baseline: {len(baseline):,} chars")
        else:
            print("Baseline: (none)")
        if failed_path:
            print(f"Latest failure: {failed_path.name} ({len(failed_html):,} chars)")
        else:
            print("Latest failure: (none)")


if __name__ == "__main__":
    main()
