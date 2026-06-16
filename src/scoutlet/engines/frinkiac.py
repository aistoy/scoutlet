"""Frinkiac (Simpsons screenshot search) - adapted from SearXNG."""

import logging
from json import loads
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.frinkiac")

about = {
    "website": "https://frinkiac.com",
    "wikidata_id": "Q24882614",
    "official_api_documentation": {"url": None, "comment": "see https://github.com/MitchellAW/CompuGlobal"},
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["images"]

BASE = "https://frinkiac.com/"
SEARCH_URL = "{base}api/search?{query}"
RESULT_URL = "{base}?{query}"
THUMB_URL = "{base}img/{episode}/{timestamp}/medium.jpg"
IMAGE_URL = "{base}img/{episode}/{timestamp}.jpg"


def request(query, params):
    params["url"] = SEARCH_URL.format(base=BASE, query=urlencode({"q": query}))
    return params


def response(resp):
    results = []
    response_data = loads(resp.text)
    for result in response_data:
        episode = result.get("Episode", "")
        timestamp = result.get("Timestamp", "")
        title = result.get("Title") or episode
        content = result.get("Content", "")

        results.append({
            "template": "images.html",
            "url": RESULT_URL.format(base=BASE, query=urlencode({"p": "caption", "e": episode, "t": timestamp})),
            "title": title,
            "content": content,
            "thumbnail_src": THUMB_URL.format(base=BASE, episode=episode, timestamp=timestamp),
            "img_src": IMAGE_URL.format(base=BASE, episode=episode, timestamp=timestamp),
        })

    return results
