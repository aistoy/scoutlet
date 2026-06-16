"""Peertube (videos) - adapted from SearXNG.

Changes:
- Removed fetch_traits + babel locale mapping (engine works without language filter)
- Replaced dateutil.parser with datetime.fromisoformat
- Replaced humanize_number with local formatter
"""

import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from scoutlet.utils import html_to_text

logger = logging.getLogger("scoutlet.engines.peertube")

about = {
    "website": "https://joinpeertube.org",
    "wikidata_id": "Q50938515",
    "official_api_documentation": "https://docs.joinpeertube.org/api-rest-reference.html#tag/Search/operation/searchVideos",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["videos"]
paging = True
base_url = "https://peer.tube"

time_range_support = True
time_range_table = {
    "day": timedelta(),
    "week": timedelta(weeks=-1),
    "month": timedelta(days=-30),
    "year": timedelta(days=-365),
}

safesearch = True
safesearch_table = {0: "both", 1: "false", 2: "false"}


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _humanize_number(n):
    try:
        n = int(n)
    except (ValueError, TypeError):
        return "0"
    for unit in ["", "K", "M", "B"]:
        if abs(n) < 1000:
            return f"{n}{unit}"
        n //= 1000
    return f"{n}T+"


def request(query, params):
    if not query:
        return None

    params["url"] = (
        base_url.rstrip("/") + "/api/v1/search/videos?"
        + urlencode({
            "search": query,
            "searchTarget": "search-index",
            "resultType": "videos",
            "start": (params["pageno"] - 1) * 10,
            "count": 10,
            "sort": "-match",
            "nsfw": safesearch_table.get(params.get("safesearch", 0), "both"),
        })
    )

    if params.get("time_range") in time_range_table:
        time = datetime.now().date() + time_range_table[params["time_range"]]
        params["url"] += "&startDate=" + time.isoformat()

    return params


def video_response(resp):
    results = []
    json_data = resp.json()

    if "data" not in json_data:
        return []

    for result in json_data["data"]:
        channel = result.get("channel") or {}
        metadata = [
            x for x in [
                channel.get("displayName"),
                (channel.get("name", "") + "@" + channel.get("host", "")) if channel.get("name") else None,
                ", ".join(result.get("tags", []) or []),
            ] if x
        ]

        duration = result.get("duration")
        if duration:
            try:
                duration = timedelta(seconds=duration)
            except (ValueError, TypeError):
                duration = None

        account = result.get("account") or {}
        results.append({
            "url": result.get("url", ""),
            "title": result.get("name", ""),
            "content": html_to_text(result.get("description") or ""),
            "author": account.get("displayName"),
            "length": duration,
            "views": _humanize_number(result.get("views", 0)),
            "template": "videos.html",
            "publishedDate": _parse_date(result.get("publishedAt")),
            "iframe_src": result.get("embedUrl", ""),
            "thumbnail": result.get("thumbnailUrl") or result.get("previewUrl") or "",
            "metadata": " | ".join(metadata),
        })

    return results


def response(resp):
    return video_response(resp)
