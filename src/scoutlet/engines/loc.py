"""Library of Congress photos - adapted from SearXNG."""

import logging
from urllib.parse import urlencode

from scoutlet.network import raise_for_httperror

logger = logging.getLogger("scoutlet.engines.loc")

about = {
    "website": "https://www.loc.gov/pictures/",
    "wikidata_id": "Q131454",
    "official_api_documentation": "https://www.loc.gov/api",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["images"]
paging = True

endpoint = "photos"
base_url = "https://www.loc.gov"
search_string = "/{endpoint}/?sp={page}&{query}&fo=json"


def request(query, params):
    search_path = search_string.format(
        endpoint=endpoint,
        query=urlencode({"q": query}),
        page=params["pageno"],
    )
    params["url"] = base_url + search_path
    params["raise_for_httperror"] = False
    return params


def response(resp):
    results = []
    json_data = resp.json()

    json_results = json_data.get("results")
    if not json_results:
        if json_data.get("status") == 404:
            return results

    raise_for_httperror(resp)

    for result in json_results or []:
        item = result.get("item") or {}
        url = item.get("link")
        if not url:
            continue

        img_list = result.get("image_url")
        if not img_list:
            continue

        title = result.get("title", "")
        if title.startswith("["):
            title = title.strip("[]")

        content_items = [
            item.get("created_published_date"),
            (item.get("summary", [None]) or [None])[0],
            (item.get("notes", [None]) or [None])[0],
            (item.get("part_of", [None]) or [None])[0],
        ]

        author = None
        if item.get("creators"):
            author = item["creators"][0].get("title")

        results.append({
            "template": "images.html",
            "url": url,
            "title": title,
            "content": " / ".join([str(i) for i in content_items if i]),
            "img_src": img_list[-1],
            "thumbnail_src": img_list[0],
            "author": author,
        })

    return results
