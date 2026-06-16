"""Dailymotion (videos) - adapted from SearXNG.

Changes:
- Removed fetch_traits + babel locale mapping (engine works without locale filtering)
- from searx.* -> from scoutlet.*
"""

import time
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from scoutlet.network import raise_for_httperror
from scoutlet.exceptions import SearchEngineAPIException
from scoutlet.utils import html_to_text

logger = logging.getLogger("scoutlet.engines.dailymotion")

about = {
    "website": "https://www.dailymotion.com",
    "wikidata_id": "Q769222",
    "official_api_documentation": "https://www.dailymotion.com/developer",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["videos"]
paging = True
number_of_results = 10
time_range_support = True
time_delta_dict = {
    "day": timedelta(days=1),
    "week": timedelta(days=7),
    "month": timedelta(days=31),
    "year": timedelta(days=365),
}

safesearch = True
safesearch_params = {
    2: {"is_created_for_kids": "true"},
    1: {"is_created_for_kids": "true"},
    0: {},
}
family_filter_map = {2: "true", 1: "true", 0: "false"}

result_fields = [
    "allow_embed", "description", "title", "created_time",
    "duration", "url", "thumbnail_360_url", "id",
]

search_url = "https://api.dailymotion.com/videos?"
iframe_src_template = "https://www.dailymotion.com/embed/video/{video_id}"


def request(query, params):
    if not query:
        return None

    args = {
        "search": query,
        "family_filter": family_filter_map.get(params.get("safesearch", 0), "false"),
        "thumbnail_ratio": "original",
        "languages": "en",
        "page": params["pageno"],
        "password_protected": "false",
        "private": "false",
        "sort": "relevance",
        "limit": number_of_results,
        "fields": ",".join(result_fields),
    }
    args.update(safesearch_params.get(params.get("safesearch", 0), {}))

    time_delta = time_delta_dict.get(params.get("time_range"))
    if time_delta:
        created_after = datetime.now() - time_delta
        args["created_after"] = datetime.timestamp(created_after)

    params["url"] = search_url + urlencode(args)
    return params


def response(resp):
    results = []
    search_res = resp.json()

    if "error" in search_res:
        raise SearchEngineAPIException((search_res.get("error") or {}).get("message", "Dailymotion API error"))

    raise_for_httperror(resp)

    for res in search_res.get("list", []):
        title = res.get("title", "")
        url = res.get("url", "")

        content = html_to_text(res.get("description", "") or "")
        if len(content) > 300:
            content = content[:300] + "..."

        publishedDate = None
        if res.get("created_time"):
            try:
                publishedDate = datetime.fromtimestamp(res["created_time"])
            except (ValueError, TypeError, OSError):
                pass

        length = ""
        if res.get("duration"):
            gm = time.gmtime(res["duration"])
            length = time.strftime("%H:%M:%S", gm) if gm.tm_hour else time.strftime("%M:%S", gm)

        thumbnail = (res.get("thumbnail_360_url") or "").replace("http://", "https://")

        item = {
            "template": "videos.html",
            "url": url,
            "title": title,
            "content": content,
            "publishedDate": publishedDate,
            "length": length,
            "thumbnail": thumbnail,
        }

        if res.get("allow_embed"):
            item["iframe_src"] = iframe_src_template.format(video_id=res.get("id", ""))

        results.append(item)

    return results
