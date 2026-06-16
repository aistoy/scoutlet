"""MRS - Matrix Rooms Search (social media) - adapted from SearXNG.

Requires `base_url` to be set:
    load_engines(engine_configs={"mrs": {"base_url": "https://mrs-host"}})
"""

import logging
from urllib.parse import quote_plus

logger = logging.getLogger("scoutlet.engines.mrs")

about = {
    "website": "https://matrixrooms.info",
    "wikidata_id": None,
    "official_api_documentation": "https://gitlab.com/etke.cc/mrs/api/-/blob/main/openapi.yml?ref_type=heads",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

paging = True
categories = ["social media"]

base_url = ""
matrix_url = "https://matrix.to"
page_size = 20


def setup(engine_settings):
    if not base_url:
        logger.error("MRS engine: base_url is unset")
        return False
    return True


def request(query, params):
    params["url"] = f"{base_url}/search/{quote_plus(query)}/{page_size}/{(params['pageno']-1)*page_size}"
    return params


def response(resp):
    results = []

    for result in resp.json():
        results.append({
            "url": matrix_url + "/#/" + result.get("alias", ""),
            "title": result.get("name", ""),
            "content": (result.get("topic", "") or "")
                + f" // {result.get('members', 0)} members"
                + f" // {result.get('alias', '')}"
                + f" // {result.get('server', '')}",
            "thumbnail": result.get("avatar_url"),
        })

    return results
