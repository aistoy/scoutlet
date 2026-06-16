"""Mixcloud (music) - adapted from SearXNG."""

import logging
from urllib.parse import urlencode
from datetime import datetime

logger = logging.getLogger("scoutlet.engines.mixcloud")

about = {
    "website": "https://www.mixcloud.com/",
    "wikidata_id": "Q6883832",
    "official_api_documentation": "http://www.mixcloud.com/developers/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["music"]
paging = True

url = "https://api.mixcloud.com/"
search_url = url + "search/?{query}&type=cloudcast&limit=10&offset={offset}"
iframe_src_template = "https://www.mixcloud.com/widget/iframe/?feed={url}"


def request(query, params):
    offset = (params["pageno"] - 1) * 10
    params["url"] = search_url.format(query=urlencode({"q": query}), offset=offset)
    return params


def response(resp):
    results = []
    search_res = resp.json()

    for result in search_res.get("data", []):
        r_url = result.get("url", "")
        publishedDate = None
        if result.get("created_time"):
            try:
                publishedDate = datetime.fromisoformat(result["created_time"].replace("Z", "+00:00"))
            except ValueError:
                pass

        pictures = result.get("pictures") or {}
        user = result.get("user") or {}
        results.append({
            "url": r_url,
            "title": result.get("name", ""),
            "iframe_src": iframe_src_template.format(url=r_url),
            "thumbnail": pictures.get("medium", ""),
            "publishedDate": publishedDate,
            "content": user.get("name", ""),
        })

    return results
