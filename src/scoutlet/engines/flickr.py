"""Flickr (Images) - adapted from SearXNG.

Requires Flickr API key. Set via:
    load_engines(engine_configs={"flickr": {"api_key": "..."}})
"""

import logging
from json import loads
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.flickr")

about = {
    "website": "https://www.flickr.com",
    "wikidata_id": "Q103204",
    "official_api_documentation": "https://secure.flickr.com/services/api/flickr.photos.search.html",
    "use_official_api": True,
    "require_api_key": True,
    "results": "JSON",
}

categories = ["images"]

nb_per_page = 15
paging = True
api_key = None

url = (
    "https://api.flickr.com/services/rest/?method=flickr.photos.search"
    + "&api_key={api_key}&{text}&sort=relevance"
    + "&extras=description%2C+owner_name%2C+url_o%2C+url_n%2C+url_z"
    + "&per_page={nb_per_page}&format=json&nojsoncallback=1&page={page}"
)
photo_url = "https://www.flickr.com/photos/{userid}/{photoid}"


def build_flickr_url(user_id, photo_id):
    return photo_url.format(userid=user_id, photoid=photo_id)


def request(query, params):
    params["url"] = url.format(
        text=urlencode({"text": query}),
        api_key=api_key,
        nb_per_page=nb_per_page,
        page=params["pageno"],
    )
    return params


def response(resp):
    results = []
    search_results = loads(resp.text)

    if "photos" not in search_results:
        return []
    if "photo" not in search_results["photos"]:
        return []

    for photo in search_results["photos"]["photo"]:
        if "url_o" in photo:
            img_src = photo["url_o"]
        elif "url_z" in photo:
            img_src = photo["url_z"]
        else:
            continue

        if "url_n" in photo:
            thumbnail_src = photo["url_n"]
        elif "url_z" in photo:
            thumbnail_src = photo["url_z"]
        else:
            thumbnail_src = img_src

        description = photo.get("description") or {}
        results.append({
            "url": build_flickr_url(photo.get("owner", ""), photo.get("id", "")),
            "title": photo.get("title", ""),
            "img_src": img_src,
            "thumbnail_src": thumbnail_src,
            "content": description.get("_content", ""),
            "author": photo.get("ownername", ""),
            "template": "images.html",
        })

    return results
