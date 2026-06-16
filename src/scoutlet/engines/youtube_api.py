"""YouTube Data API v3 - adapted from SearXNG.

Requires YouTube API key. Set via:
    load_engines(engine_configs={"youtube_api": {"api_key": "..."}})
"""

import logging
from json import loads
from urllib.parse import urlencode
from datetime import datetime

from scoutlet.exceptions import SearchEngineAPIException

logger = logging.getLogger("scoutlet.engines.youtube_api")

about = {
    "website": "https://www.youtube.com/",
    "wikidata_id": "Q866",
    "official_api_documentation": "https://developers.google.com/youtube/v3/docs/search/list",
    "use_official_api": True,
    "require_api_key": True,
    "results": "JSON",
}

categories = ["videos", "music"]
paging = False
api_key = None

base_url = "https://www.googleapis.com/youtube/v3/search"
search_url = base_url + "?part=snippet&{query}&maxResults=20&key={api_key}"
base_youtube_url = "https://www.youtube.com/watch?v="


def setup(engine_settings):
    if api_key and api_key not in ("unset", "..."):
        return True
    logger.error("YouTube Data API engine: api_key is not set")
    return False


def request(query, params):
    params["url"] = search_url.format(query=urlencode({"q": query}), api_key=api_key)
    if params.get("language", "all") != "all":
        params["url"] += "&relevanceLanguage=" + params["language"].split("-")[0]
    return params


def response(resp):
    results = []
    search_results = loads(resp.text)

    if "error" in search_results and "message" in (search_results.get("error") or {}):
        raise SearchEngineAPIException(search_results["error"]["message"])

    if "items" not in search_results:
        return []

    for result in search_results["items"]:
        rid = result.get("id") or {}
        if "videoId" not in rid:
            continue

        videoid = rid["videoId"]
        snippet = result.get("snippet") or {}
        title = snippet.get("title", "")
        content = snippet.get("description", "")
        thumbnail = ""
        thumbnails = snippet.get("thumbnails") or {}
        if "high" in thumbnails:
            thumbnail = thumbnails["high"].get("url", "")

        publishedDate = None
        if snippet.get("publishedAt"):
            try:
                publishedDate = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            except ValueError:
                pass

        results.append({
            "url": base_youtube_url + videoid,
            "title": title,
            "content": content,
            "template": "videos.html",
            "publishedDate": publishedDate,
            "iframe_src": "https://www.youtube-nocookie.com/embed/" + videoid,
            "thumbnail": thumbnail,
        })

    return results
