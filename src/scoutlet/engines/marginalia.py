"""Marginalia search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced searxng_useragent() with gen_useragent()
- Removed TypedDict classes and TYPE_CHECKING blocks
- Replaced res.types.MainResult with plain dicts
- Kept init() function
- Return list[dict] from response()
"""

import logging

from scoutlet.utils import gen_useragent

logger = logging.getLogger("scoutlet.engines.marginalia")

about = {
    "website": "https://www.marginalia.nu/",
    "wikidata_id": "Q114975054",
    "official_api_documentation": "https://www.marginalia.nu/#api",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["general"]
paging = True
supported_languages = ["en"]

search_url = "https://www.marginalia.nu/{profile}/search?{query}"
profile = "minor"


def init(engine_settings=None):
    """Initialize the marginalia engine."""
    global profile
    # Can be set to "marginalia" or "minor" via engine config
    if engine_settings and hasattr(engine_settings, "profile"):
        profile = engine_settings.profile


def request(query, params):
    from urllib.parse import urlencode

    args = urlencode({
        "q": query,
        "count": 20,
        "index": (params["pageno"] - 1),
    })
    params["url"] = search_url.format(profile=profile, query=args)
    params["headers"]["User-Agent"] = gen_useragent()
    return params


def response(resp):
    results = []
    try:
        data = resp.json()
    except Exception:
        return results

    for item in data.get("results", []):
        title = item.get("title", "")
        url = item.get("url", "")
        description = item.get("description", "")
        quality = item.get("quality", 0)

        results.append({
            "url": url,
            "title": title,
            "content": description,
            "score": quality,
        })

    return results
