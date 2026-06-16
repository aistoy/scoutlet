"""Tube Archivist (videos, self-hosted) - adapted from SearXNG.

Requires `base_url` and `ta_token` to be set:
    load_engines(engine_configs={"tubearchivist": {
        "base_url": "http://your-instance:port",
        "ta_token": "...",
    }})
"""

import logging
from urllib.parse import urlencode
from datetime import datetime

from scoutlet.utils import html_to_text

logger = logging.getLogger("scoutlet.engines.tubearchivist")

about = {
    "website": "https://www.tubearchivist.com",
    "official_api_documentation": "https://docs.tubearchivist.com/api/introduction/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["videos"]
paging = True

base_url = ""
ta_token = ""
ta_link_to_mp4 = False


def _humanize_number(n):
    try:
        n = int(n)
    except (ValueError, TypeError):
        return "0"
    for unit in ["", "K", "M", "B"]:
        if abs(n) < 1000:
            return f"{n}{unit}"
        n //= 1000
    return f"{n}T+"


def setup(engine_settings):
    if not base_url:
        logger.error("tubearchivist engine: base_url is unset")
        return False
    if not ta_token:
        logger.error("tubearchivist engine: ta_token is unset")
        return False
    return True


def absolute_url(relative_url):
    return f"{base_url.rstrip('/')}{relative_url}"


def request(query, params):
    if not query:
        return None

    args = {"query": query}
    params["url"] = f"{base_url.rstrip('/')}/api/search/?{urlencode(args)}"
    params["headers"]["Authorization"] = f"Token {ta_token}"
    return params


def response(resp):
    results = []
    json_data = resp.json()

    if "results" not in json_data:
        return results

    res_obj = json_data["results"]

    for channel_result in res_obj.get("channel_results", []):
        channel_url = absolute_url(f'/channel/{channel_result.get("channel_id", "")}')
        results.append({
            "url": channel_url,
            "title": channel_result.get("channel_name", ""),
            "content": html_to_text(channel_result.get("channel_description", "")),
            "author": channel_result.get("channel_name", ""),
            "views": _humanize_number(channel_result.get("channel_subs", 0)),
            "thumbnail": f'{absolute_url(channel_result.get("channel_thumb_url", ""))}?auth={ta_token}',
        })

    for video_result in res_obj.get("video_results", []):
        metadata = list(filter(None, [
            (video_result.get("channel") or {}).get("channel_name"),
            *video_result.get("tags", []),
        ]))[:5]

        if ta_link_to_mp4:
            url = f'{base_url.rstrip("/")}{video_result.get("media_url", "")}'
        else:
            url = f'{base_url.rstrip("/")}/?videoId={video_result.get("youtube_id", "")}'

        publishedDate = None
        if video_result.get("published"):
            try:
                publishedDate = datetime.fromisoformat(video_result["published"].replace("Z", "+00:00"))
            except ValueError:
                pass

        player = video_result.get("player") or {}
        stats = video_result.get("stats") or {}

        results.append({
            "template": "videos.html",
            "url": url,
            "title": video_result.get("title", ""),
            "content": html_to_text(video_result.get("description", "")),
            "author": (video_result.get("channel") or {}).get("channel_name", ""),
            "length": player.get("duration_str", ""),
            "views": _humanize_number(stats.get("view_count", 0)),
            "publishedDate": publishedDate,
            "thumbnail": f'{absolute_url(video_result.get("vid_thumb_url", ""))}?auth={ta_token}',
            "metadata": " | ".join(metadata),
        })

    return results
