"""Spotify (music) - adapted from SearXNG.

Requires Spotify API client credentials. Set via:
    load_engines(engine_configs={"spotify": {
        "api_client_id": "...",
        "api_client_secret": "...",
    }})
"""

import logging
import base64
from json import loads
from urllib.parse import urlencode

from scoutlet.network import post as http_post

logger = logging.getLogger("scoutlet.engines.spotify")

about = {
    "website": "https://www.spotify.com",
    "wikidata_id": "Q689141",
    "official_api_documentation": "https://developer.spotify.com/web-api/search-item/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["music"]
paging = True
api_client_id = None
api_client_secret = None

url = "https://api.spotify.com/"
search_url = url + "v1/search?{query}&type=track&offset={offset}"


def setup(engine_settings):
    if api_client_id and api_client_secret:
        return True
    logger.error("Spotify engine: api_client_id and api_client_secret are required")
    return False


def request(query, params):
    offset = (params["pageno"] - 1) * 20
    params["url"] = search_url.format(query=urlencode({"q": query}), offset=offset)

    try:
        r = http_post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            headers={
                "Authorization": "Basic " + base64.b64encode(
                    "{}:{}".format(api_client_id, api_client_secret).encode()
                ).decode(),
            },
        )
        j = loads(r.text)
        params["headers"] = {"Authorization": "Bearer {}".format(j.get("access_token", ""))}
    except Exception:
        logger.exception("Spotify token fetch failed")
        params["headers"] = {}

    return params


def response(resp):
    results = []
    search_res = loads(resp.text)

    tracks = (search_res.get("tracks") or {}).get("items") or []
    for result in tracks:
        if result.get("type") != "track":
            continue
        title = result.get("name", "")
        external_urls = result.get("external_urls") or {}
        link = external_urls.get("spotify", "")
        artists = result.get("artists") or []
        album = result.get("album") or {}
        artist_name = artists[0].get("name", "") if artists else ""
        content = "{} - {} - {}".format(artist_name, album.get("name", ""), title)

        results.append({
            "url": link,
            "title": title,
            "iframe_src": "https://embed.spotify.com/?uri=spotify:track:" + result.get("id", ""),
            "content": content,
        })

    return results
