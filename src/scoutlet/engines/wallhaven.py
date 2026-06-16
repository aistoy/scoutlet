"""Wallhaven image search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Already used datetime.strptime, kept as-is
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
"""

import logging
from datetime import datetime
from urllib.parse import urlencode

from scoutlet.utils import humanize_bytes

logger = logging.getLogger("scoutlet.engines.wallhaven")

about = {
    "website": "https://wallhaven.cc/",
    "wikidata_id": "Q119923865",
    "official_api_documentation": "https://wallhaven.cc/help/api",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["images"]
paging = True

api_key = ""
search_url = "https://wallhaven.cc/api/v1/search?{query}"

# Possible categories: general, anime, people
# Possible purities: sfw, sketchy, nsfw (nsfw requires API key)


def request(query, params):
    args = urlencode({
        "q": query,
        "page": params["pageno"],
    })
    params["url"] = search_url.format(query=args)
    if api_key:
        params["headers"]["X-API-Key"] = api_key
    return params


def response(resp):
    results = []
    data = resp.json()

    for item in data.get("data", []):
        resolution = item.get("resolution", "")
        file_size = item.get("file_size", 0)
        category = item.get("category", "")

        content_parts = []
        if resolution:
            content_parts.append(resolution)
        if category:
            content_parts.append(category)
        if file_size:
            content_parts.append(humanize_bytes(file_size))

        publishedDate = None
        created_at = item.get("created_at", "")
        if created_at:
            try:
                publishedDate = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        results.append({
            "template": "images.html",
            "url": item.get("url", ""),
            "thumbnail_src": item.get("thumbs", {}).get("small", ""),
            "img_src": item.get("path", ""),
            "title": item.get("id", ""),
            "content": " | ".join(content_parts),
            "publishedDate": publishedDate,
            "resolution": resolution,
            "img_format": item.get("file_type", "").replace("image/", ""),
        })

    return results
