"""Pexels (images) - adapted from SearXNG.

Changes:
- Removed EngineCache + dynamic secret-key extraction; use module-level api_key directly.
  Set a different key via engine_configs={"pexels": {"api_key": "..."}}.
"""

import logging
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.pexels")

about = {
    "website": "https://www.pexels.com",
    "wikidata_id": "Q101240504",
    "official_api_documentation": "https://www.pexels.com/api/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

base_url = "https://www.pexels.com"
categories = ["images"]

api_key = "H2jk9uKnhRmL6WPwh89zBezWvr"

results_per_page = 20
paging = True
time_range_support = True
time_range_map = {"day": "last_24_hours", "week": "last_week", "month": "last_month", "year": "last_year"}


def request(query, params):
    args = {
        "query": query,
        "page": params["pageno"],
        "per_page": results_per_page,
    }
    if params.get("time_range"):
        args["date_from"] = time_range_map[params["time_range"]]

    params["url"] = f"{base_url}/en-us/api/v3/search/photos?{urlencode(args)}"
    params["headers"]["secret-key"] = api_key
    return params


def response(resp):
    results = []
    json_data = resp.json()

    for result in json_data.get("data", []):
        attrs = result.get("attributes") or {}
        image = attrs.get("image") or {}
        user = attrs.get("user") or {}
        results.append({
            "template": "images.html",
            "url": f"{base_url}/photo/{attrs.get('slug', '')}-{attrs.get('id', '')}/",
            "title": attrs.get("title", ""),
            "content": attrs.get("description", ""),
            "thumbnail_src": image.get("small", ""),
            "img_src": image.get("download_link", ""),
            "resolution": "%sx%s" % (attrs.get("width", "?"), attrs.get("height", "?")),
            "author": user.get("username", ""),
        })

    return results
