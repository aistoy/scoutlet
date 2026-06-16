"""iQiyi (videos) - adapted from SearXNG."""

import logging
from urllib.parse import urlencode
from datetime import datetime, timedelta

from scoutlet.exceptions import SearchEngineAPIException

logger = logging.getLogger("scoutlet.engines.iqiyi")

about = {
    "website": "https://www.iqiyi.com/",
    "wikidata_id": "Q15913890",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
    "language": "zh",
}

paging = True
time_range_support = True
categories = ["videos"]

time_range_dict = {"day": "1", "week": "2", "month": "3"}

base_url = "https://mesh.if.iqiyi.com"


def request(query, params):
    query_params = {"key": query, "pageNum": params["pageno"], "pageSize": 25}
    if time_range_dict.get(params.get("time_range", "")):
        query_params["sitePublishDate"] = time_range_dict[params["time_range"]]

    params["url"] = f"{base_url}/portal/lw/search/homePageV3?{urlencode(query_params)}"
    return params


def _result(video, album_info):
    length = timedelta(milliseconds=video.get("duration", 0))

    published_date = None
    release_time = (album_info.get("releaseTime") or {}).get("value")
    if release_time:
        try:
            published_date = datetime.strptime(release_time, "%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    return {
        "url": (video.get("pageUrl") or "").replace("http://", "https://"),
        "title": video.get("title", ""),
        "content": (album_info.get("brief") or {}).get("value", ""),
        "template": "videos.html",
        "length": length,
        "publishedDate": published_date,
        "thumbnail": album_info.get("img", ""),
    }


def response(resp):
    try:
        data = resp.json()
    except Exception as e:
        raise SearchEngineAPIException(f"Invalid response: {e}") from e
    results = []

    if "data" not in data or "templates" not in data["data"]:
        raise SearchEngineAPIException("Invalid response")

    for entry in data["data"]["templates"]:
        album_info = entry.get("albumInfo", {})
        if "videos" in album_info:
            for video in album_info["videos"]:
                results.append(_result(video, album_info))
        else:
            results.append(_result(album_info, album_info))

    return results
