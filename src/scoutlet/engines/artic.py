"""Art Institute of Chicago - adapted from SearXNG."""

import logging
from json import loads
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.artic")

about = {
    "website": "https://www.artic.edu",
    "wikidata_id": "Q239303",
    "official_api_documentation": "http://api.artic.edu/docs/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["images"]
paging = True
nb_per_page = 20

search_api = "https://api.artic.edu/api/v1/artworks/search?"
image_api = "https://www.artic.edu/iiif/2/"


def request(query, params):
    args = urlencode({
        "q": query,
        "page": params["pageno"],
        "fields": "id,title,artist_display,medium_display,image_id,date_display,dimensions,artist_titles",
        "limit": nb_per_page,
    })
    params["url"] = search_api + args
    return params


def response(resp):
    results = []
    json_data = loads(resp.text)

    for result in json_data.get("data", []):
        if not result.get("image_id"):
            continue

        results.append({
            "url": "https://artic.edu/artworks/%s" % result.get("id", ""),
            "title": "%s (%s) // %s" % (
                result.get("title", ""),
                result.get("date_display", ""),
                result.get("artist_display", ""),
            ),
            "content": "%s // %s" % (
                result.get("medium_display", ""),
                result.get("dimensions", ""),
            ),
            "author": ", ".join(result.get("artist_titles") or []),
            "img_src": image_api + "/%s/full/843,/0/default.jpg" % result["image_id"],
            "template": "images.html",
        })

    return results
