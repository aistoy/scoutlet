"""Yandex Music - adapted from SearXNG."""

import logging
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.yandex_music")

about = {
    "website": "https://music.yandex.ru",
    "wikidata_id": "Q4537983",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["music"]
paging = True

url = "https://music.yandex.ru"
search_url = url + "/handlers/music-search.jsx"


def request(query, params):
    args = {"text": query, "page": params["pageno"] - 1}
    params["url"] = search_url + "?" + urlencode(args)
    return params


def response(resp):
    results = []
    search_res = resp.json()

    tracks = (search_res.get("tracks") or {}).get("items") or []
    for result in tracks:
        if result.get("type") != "music":
            continue
        track_id = result.get("id", "")
        albums = result.get("albums") or []
        if not albums:
            continue
        album_id = albums[0].get("id", "")
        artists = result.get("artists") or []
        artist_name = artists[0].get("name", "") if artists else ""

        results.append({
            "url": f"{url}/album/{album_id}/track/{track_id}",
            "title": result.get("title", ""),
            "content": f"[{albums[0].get('title', '')}] {artist_name} - {result.get('title', '')}",
            "iframe_src": f"{url}/iframe/track/{track_id}/{album_id}",
        })

    return results
