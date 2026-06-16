"""Odysee (videos) - adapted from SearXNG.

Changes:
- Removed fetch_traits + babel locale mapping (engine works without language filter)
"""

import time
import logging
from datetime import datetime
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.odysee")

about = {
    "website": "https://odysee.com/",
    "wikidata_id": "Q102046570",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

paging = True
time_range_support = True
results_per_page = 20
categories = ["videos"]

base_url = "https://lighthouse.odysee.tv/search"


def request(query, params):
    time_range_dict = {
        "day": "today",
        "week": "thisweek",
        "month": "thismonth",
        "year": "thisyear",
    }

    start_index = (params["pageno"] - 1) * results_per_page
    query_params = {
        "s": query,
        "size": results_per_page,
        "from": start_index,
        "include": "channel,thumbnail_url,title,description,duration,release_time",
        "mediaType": "video",
    }

    if params.get("time_range") in time_range_dict:
        query_params["time_filter"] = time_range_dict[params["time_range"]]

    params["url"] = f"{base_url}?{urlencode(query_params)}"
    return params


def format_duration(duration):
    try:
        seconds = int(duration)
    except (ValueError, TypeError):
        return ""
    length = time.gmtime(seconds)
    if length.tm_hour:
        return time.strftime("%H:%M:%S", length)
    return time.strftime("%M:%S", length)


def response(resp):
    data = resp.json()
    results = []

    for item in data:
        name = item.get("name", "")
        claim_id = item.get("claimId", "")
        title = item.get("title", "")
        thumbnail_url = item.get("thumbnail_url", "")
        description = item.get("description") or ""
        channel = item.get("channel", "")
        release_time = item.get("release_time", "")
        duration = item.get("duration", 0)

        publishedDate = None
        if release_time:
            try:
                publishedDate = datetime.strptime(release_time.split("T")[0], "%Y-%m-%d")
            except ValueError:
                pass

        url = f"https://odysee.com/{name}:{claim_id}"
        iframe_url = f"https://odysee.com/$/embed/{name}:{claim_id}"
        odysee_thumbnail = f"https://thumbnails.odycdn.com/optimize/s:390:0/quality:85/plain/{thumbnail_url}"
        formatted_duration = format_duration(duration)

        results.append({
            "title": title,
            "url": url,
            "content": description,
            "author": channel,
            "publishedDate": publishedDate,
            "length": formatted_duration,
            "thumbnail": odysee_thumbnail,
            "iframe_src": iframe_url,
            "template": "videos.html",
        })

    return results
