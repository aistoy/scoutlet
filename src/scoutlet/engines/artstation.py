"""Artstation - adapted from SearXNG.

Changes from SearXNG original:
- Removed EngineCache; CSRF tokens cached in module-global with simple expiry
- from searx.network.post -> from scoutlet.network.post
- Return list[dict]
"""

import logging
import re
import time
from json import dumps
from typing import Any

from scoutlet.network import post

logger = logging.getLogger("scoutlet.engines.artstation")

about = {
    "website": "https://www.artstation.com/",
    "wikidata_id": "Q65551500",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

paging = True
categories = ["images"]
results_per_page = 20

base_url = "https://www.artstation.com/api/v2/search/projects.json"
csrf_token_url = "https://www.artstation.com/api/v2/csrf_protection/token.json"
KEY_EXPIRATION_SECONDS = 3600

# Simple module-global cache (no persistence)
_csrf_cache: dict[str, Any] = {"public": None, "private": None, "expires": 0.0}


def _fetch_csrf_tokens():
    now = time.time()
    if _csrf_cache["public"] and _csrf_cache["private"] and _csrf_cache["expires"] > now:
        return _csrf_cache["public"], _csrf_cache["private"]

    resp = post(csrf_token_url)
    public_token = resp.json().get("public_csrf_token", "")
    private_token = resp.cookies.get("PRIVATE-CSRF-TOKEN", "")

    _csrf_cache["public"] = public_token
    _csrf_cache["private"] = private_token
    _csrf_cache["expires"] = now + KEY_EXPIRATION_SECONDS

    return public_token, private_token


def request(query, params):
    try:
        public_token, private_token = _fetch_csrf_tokens()
    except Exception:
        logger.exception("Failed to fetch artstation CSRF tokens")
        public_token, private_token = "", ""

    form_data = {
        "query": query,
        "page": params["pageno"],
        "per_page": results_per_page,
        "sorting": "relevance",
        "pro_first": 1,
    }

    params["url"] = base_url
    params["method"] = "POST"
    params["headers"]["content-type"] = "application/json"
    params["headers"]["PUBLIC-CSRF-TOKEN"] = public_token
    if private_token:
        params["cookies"] = {"PRIVATE-CSRF-TOKEN": private_token}
    params["data"] = dumps(form_data)

    return params


def response(resp):
    results = []
    search_res = resp.json()

    for item in search_res.get("data", []):
        thumb = item.get("smaller_square_cover_url", "")
        fullsize_image = re.sub(r"/\d{6,}/", "/", thumb).replace("smaller_square", "large") if thumb else ""

        user = item.get("user") or {}
        results.append({
            "template": "images.html",
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "author": "%s (%s)" % (user.get("username", ""), user.get("full_name", "")),
            "img_src": fullsize_image,
            "thumbnail_src": thumb,
        })

    return results
