"""9GAG (social media) - adapted from SearXNG.

Note: original module name is `9gag.py` which starts with a digit; the engine
loader uses spec_from_file_location which accepts any string, so loading works.
"""

import logging
from json import loads
from datetime import datetime
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.9gag")

about = {
    "website": "https://9gag.com/",
    "wikidata_id": "Q277421",
    "official_api_documentation": None,
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["social media"]
paging = True

search_url = "https://9gag.com/v1/search-posts?{query}"
page_size = 10


def request(query, params):
    query = urlencode({"query": query, "c": (params["pageno"] - 1) * page_size})
    params["url"] = search_url.format(query=query)
    return params


def response(resp):
    results = []
    body = loads(resp.text)
    json_results = body.get("data", {})

    for result in json_results.get("posts", []):
        result_type = result.get("type")
        images = result.get("images") or {}

        image700 = images.get("image700") or {}
        thumbnail = ""
        if image700.get("height", 0) > 400:
            fb = images.get("imageFbThumbnail") or {}
            thumbnail = fb.get("url", "")
        else:
            thumbnail = image700.get("url", "")

        publishedDate = None
        if result.get("creationTs"):
            try:
                publishedDate = datetime.fromtimestamp(result["creationTs"])
            except (ValueError, TypeError, OSError):
                pass

        if result_type == "Photo":
            results.append({
                "template": "images.html",
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "content": result.get("description", ""),
                "publishedDate": publishedDate,
                "img_src": image700.get("url", ""),
                "thumbnail_src": thumbnail,
            })
        elif result_type == "Animated":
            image460sv = images.get("image460sv") or {}
            results.append({
                "template": "videos.html",
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "content": result.get("description", ""),
                "publishedDate": publishedDate,
                "thumbnail": thumbnail,
                "iframe_src": image460sv.get("url"),
            })

    for suggestion in json_results.get("tags", []):
        results.append({"suggestion": suggestion.get("key", "")})

    return results
