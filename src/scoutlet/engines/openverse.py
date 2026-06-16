"""Openverse - adapted from SearXNG."""

import logging
from json import loads
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.openverse")

about = {
    "website": "https://openverse.org/",
    "wikidata_id": None,
    "official_api_documentation": "https://api.openverse.org/v1/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["images"]
paging = True
nb_per_page = 20

base_url = "https://api.openverse.org/v1/images/"
search_string = "?page={page}&page_size={nb_per_page}&format=json&{query}"


def request(query, params):
    search_path = search_string.format(
        query=urlencode({"q": query}),
        nb_per_page=nb_per_page,
        page=params["pageno"],
    )
    params["url"] = base_url + search_path
    return params


def response(resp):
    results = []
    json_data = loads(resp.text)

    for result in json_data.get("results", []):
        results.append({
            "url": result.get("foreign_landing_url", ""),
            "title": result.get("title", ""),
            "img_src": result.get("url", ""),
            "template": "images.html",
        })

    return results
