"""Pixabay (images/videos) - adapted from SearXNG.

Changes:
- Replaced dateutil.parser with datetime.fromisoformat
- Removed enable_http2 module attribute (handled by adapter)
"""

import logging
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlencode

from scoutlet.utils import gen_useragent

logger = logging.getLogger("scoutlet.engines.pixabay")

about = {
    "website": "https://pixabay.com",
    "wikidata_id": "Q1746538",
    "official_api_documentation": "https://pixabay.com/api/docs/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

base_url = "https://pixabay.com"
categories = ["images"]
pixabay_type = "images"

paging = True
safesearch = True
time_range_support = True

safesearch_map = {0: "off", 1: "1", 2: "1"}
time_range_map = {"day": "1d", "week": "1w", "month": "1m", "year": "1y"}


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def request(query, params):
    args = {"pagi": params["pageno"]}
    if params.get("time_range"):
        args["date"] = time_range_map[params["time_range"]]

    params["url"] = f"{base_url}/{pixabay_type}/search/{quote_plus(query)}/?{urlencode(args)}"
    params["headers"] = {
        "User-Agent": gen_useragent() + " Pixabay",
        "Accept": "application/json",
        "x-bootstrap-cache-miss": "1",
        "x-fetch-bootstrap": "1",
    }
    params.setdefault("cookies", {})
    params["cookies"]["g_rated"] = safesearch_map[params.get("safesearch", 0)]
    params["allow_redirects"] = False
    return params


def _image_result(result):
    sources = list((result.get("sources") or {}).values())
    return {
        "template": "images.html",
        "url": base_url + result.get("href", ""),
        "thumbnail_src": sources[0] if sources else "",
        "img_src": sources[-1] if sources else "",
        "title": result.get("name"),
        "content": result.get("description", ""),
    }


def _video_result(result):
    sources = result.get("sources") or {}
    return {
        "template": "videos.html",
        "url": base_url + result.get("href", ""),
        "thumbnail": sources.get("thumbnail", ""),
        "iframe_src": sources.get("embed", ""),
        "title": result.get("name"),
        "content": result.get("description", ""),
        "length": timedelta(seconds=result.get("duration", 0)),
        "publishedDate": _parse_date(result.get("uploadDate")),
    }


def response(resp):
    results = []

    if resp.status_code == 302:
        return results

    json_data = resp.json()
    page = json_data.get("page", {}) or {}

    for result in page.get("results", []):
        if result.get("mediaType") in ("photo", "illustration", "vector"):
            results.append(_image_result(result))
        elif result.get("mediaType") == "video":
            results.append(_video_result(result))

    return results
