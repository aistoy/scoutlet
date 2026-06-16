"""SepiaSearch (videos) - adapted from SearXNG.

Changes:
- Removed `from searx.engines.peertube import video_response` — duplicated logic
  directly so each engine is self-contained.
- Removed fetch_traits import.
"""

import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from scoutlet.utils import html_to_text

logger = logging.getLogger("scoutlet.engines.sepiasearch")

about = {
    "website": "https://sepiasearch.org",
    "wikidata_id": None,
    "official_api_documentation": "https://docs.joinpeertube.org/api-rest-reference.html#tag/Search/operation/searchVideos",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["videos"]
paging = True

base_url = "https://sepiasearch.org"

time_range_support = True
safesearch = True
time_range_table = {
    "day": timedelta(),
    "week": timedelta(weeks=-1),
    "month": timedelta(days=-30),
    "year": timedelta(days=-365),
}
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


def response(resp):
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
