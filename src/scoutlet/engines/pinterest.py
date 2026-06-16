"""Pinterest (images) - adapted from SearXNG.

Changes:
- Removed engine_data bookmark pagination (each request fetches from page 1)
"""

import logging
from json import dumps

logger = logging.getLogger("scoutlet.engines.pinterest")

about = {
    "website": "https://www.pinterest.com/",
    "wikidata_id": "Q255381",
    "official_api_documentation": "https://developers.pinterest.com/docs/api/v5/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["images"]
paging = True

base_url = "https://www.pinterest.com"


def request(query, params):
    args = {
        "options": {
            "query": query,
            "bookmarks": [""],
        },
        "context": {},
    }
    params["url"] = f"{base_url}/resource/BaseSearchResource/get/?data={dumps(args)}"
    params["headers"] = {
        "X-Pinterest-AppState": "active",
        "X-Pinterest-Source-Url": "/ideas/",
        "X-Pinterest-PWS-Handler": "www/ideas.js",
    }
    return params


def response(resp):
    results = []
    json_resp = resp.json()

    resource_response = json_resp.get("resource_response", {}) or {}
    data = resource_response.get("data", {}) or {}

    for result in data.get("results", []):
        if result.get("type") == "story":
            continue

        main_image = (result.get("images") or {}).get("orig", {}) or {}
        images_236x = (result.get("images") or {}).get("236x", {}) or {}
        pinner = result.get("pinner") or {}
        rich_summary = result.get("rich_summary") or {}

        results.append({
            "template": "images.html",
            "url": result.get("link") or f"{base_url}/pin/{result.get('id', '')}/",
            "title": result.get("title") or result.get("grid_title", ""),
            "content": rich_summary.get("display_description") or "",
            "img_src": main_image.get("url", ""),
            "thumbnail_src": images_236x.get("url", ""),
            "source": rich_summary.get("site_name"),
            "resolution": "%sx%s" % (main_image.get("width", "?"), main_image.get("height", "?")),
            "author": "%s (%s)" % (pinner.get("full_name", ""), pinner.get("username", "")),
        })

    return results
