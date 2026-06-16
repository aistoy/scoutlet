"""360Search Videos - adapted from SearXNG.

Note: module name starts with a digit; engine_loader uses spec_from_file_location
which accepts any string as module name, so loading works despite not being a
valid Python identifier.
"""

import logging
from urllib.parse import urlencode
from datetime import datetime

from scoutlet.exceptions import SearchEngineAPIException
from scoutlet.utils import html_to_text, get_embeded_stream_url

logger = logging.getLogger("scoutlet.engines.360search_videos")

about = {
    "website": "https://tv.360kan.com/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

paging = True
results_per_page = 10
categories = ["videos"]

base_url = "https://tv.360kan.com"


def request(query, params):
    query_params = {"count": 10, "q": query, "start": params["pageno"] * 10}
    params["url"] = f"{base_url}/v1/video/list?{urlencode(query_params)}"
    return params


def response(resp):
    try:
        data = resp.json()
    except Exception as e:
        raise SearchEngineAPIException(f"Invalid response: {e}") from e
    results = []

    if "data" not in data or "result" not in data["data"]:
        raise SearchEngineAPIException("Invalid response")

    for entry in data["data"]["result"]:
        if not entry.get("title") or not entry.get("play_url"):
            continue

        published_date = None
        if entry.get("publish_time"):
            try:
                published_date = datetime.fromtimestamp(int(entry["publish_time"]))
            except (ValueError, TypeError):
                pass

        results.append({
            "url": entry["play_url"],
            "title": html_to_text(entry["title"]),
            "content": html_to_text(entry.get("description", "")),
            "template": "videos.html",
            "publishedDate": published_date,
            "thumbnail": entry.get("cover_img", ""),
            "iframe_src": get_embeded_stream_url(entry["play_url"]),
        })

    return results
