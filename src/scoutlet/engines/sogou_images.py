"""Sogou Images - adapted from SearXNG."""

import json
import logging
import re
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.sogou_images")

about = {
    "website": "https://pic.sogou.com/",
    "wikidata_id": "Q7554565",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["images"]
paging = True

base_url = "https://pic.sogou.com"


def request(query, params):
    query_params = {
        "query": query,
        "start": (params["pageno"] - 1) * 48,
    }
    params["url"] = f"{base_url}/pics?{urlencode(query_params)}"
    return params


def response(resp):
    results = []
    match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});", resp.text, re.S)
    if not match:
        return results

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return results

    search_root = data.get("searchList") or {}
    items = search_root.get("searchList") or []
    for item in items:
        results.append({
            "template": "images.html",
            "url": item.get("url", ""),
            "thumbnail_src": item.get("picUrl", ""),
            "img_src": item.get("picUrl", ""),
            "content": item.get("content_major", ""),
            "title": item.get("title", ""),
            "source": item.get("ch_site_name", ""),
        })

    return results
