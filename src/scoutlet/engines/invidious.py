"""Invidious video search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced dateutil.parser with datetime.fromtimestamp
- Imported humanize_number from scoutlet.utils
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
- Removed fetch_traits()
"""

import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

from scoutlet.utils import humanize_number

logger = logging.getLogger("scoutlet.engines.invidious")

about = {
    "website": "https://invidious.io/",
    "wikidata_id": "Q50630900",
    "official_api_documentation": "https://docs.invidious.io/api/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["videos"]
paging = True
time_range_support = True

# Default Invidious instance; can be overridden in settings
base_url = "https://inv.nadeko.net"
search_url = "{base_url}/api/v1/search?{query}"

time_range_map = {
    "day": "today",
    "week": "week",
    "month": "month",
    "year": "year",
}


def request(query, params):
    args = {
        "q": query,
        "page": params["pageno"],
        "sort_by": "relevance",
    }

    time_range = params.get("time_range")
    if time_range and time_range in time_range_map:
        args["date"] = time_range_map[time_range]

    params["url"] = search_url.format(base_url=base_url, query=urlencode(args))
    return params


def response(resp):
    results = []
    try:
        data = resp.json()
    except Exception:
        return results

    for item in data:
        if not isinstance(item, dict):
            continue
        if item.get("type", "") not in ("video",):
            continue

        publishedDate = None
        published_ts = item.get("published", 0)
        if published_ts:
            try:
                publishedDate = datetime.fromtimestamp(published_ts, tz=timezone.utc)
            except (ValueError, OSError, OverflowError):
                pass

        length_seconds = item.get("lengthSeconds", 0)
        length_str = ""
        if length_seconds:
            hours, remainder = divmod(length_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                length_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                length_str = f"{minutes}:{seconds:02d}"

        views = item.get("viewCount", 0)
        view_str = humanize_number(views) if views else ""

        content_parts = []
        if length_str:
            content_parts.append(length_str)
        if view_str:
            content_parts.append(view_str + " views")
        if item.get("description"):
            desc = item["description"]
            if len(desc) > 200:
                desc = desc[:200] + "..."
            content_parts.append(desc)

        video_id = item.get("videoId", "")
        thumbnail = item.get("videoThumbnails", [])
        thumb_url = ""
        for thumb in thumbnail:
            if isinstance(thumb, dict) and thumb.get("quality") == "medium":
                thumb_url = thumb.get("url", "")
                break
        if not thumb_url and thumbnail:
            thumb_url = thumbnail[0].get("url", "") if isinstance(thumbnail[0], dict) else ""

        results.append({
            "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
            "title": item.get("title", ""),
            "content": " | ".join(content_parts),
            "publishedDate": publishedDate,
            "thumbnail": thumb_url,
            "template": "videos.html",
            "length": length_str,
            "views": views,
        })

    return results
