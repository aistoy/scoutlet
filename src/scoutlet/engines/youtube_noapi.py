"""YouTube (videos, no API key) - adapted from SearXNG.

Changes:
- Removed engine_data next_page_token pagination (first-page only)
"""

import logging
from functools import reduce
from json import loads
from urllib.parse import quote_plus

from scoutlet.utils import extr

logger = logging.getLogger("scoutlet.engines.youtube_noapi")

about = {
    "website": "https://www.youtube.com/",
    "wikidata_id": "Q866",
    "official_api_documentation": "https://developers.google.com/youtube/v3/docs/search/list",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["videos", "music"]
paging = True
language_support = False
time_range_support = True

base_url = "https://www.youtube.com/results"
search_url = base_url + "?search_query={query}&page={page}"
time_range_url = "&sp=EgII{time_range}%253D%253D"
time_range_dict = {"day": "Ag", "week": "Aw", "month": "BA", "year": "BQ"}

base_youtube_url = "https://www.youtube.com/watch?v="


def request(query, params):
    params.setdefault("cookies", {})
    params["cookies"]["CONSENT"] = "YES+"
    params["url"] = search_url.format(query=quote_plus(query), page=params["pageno"])
    if params.get("time_range") in time_range_dict:
        params["url"] += time_range_url.format(time_range=time_range_dict[params["time_range"]])
    return params


def get_text_from_json(element):
    if not isinstance(element, dict):
        return ""
    if "runs" in element:
        return reduce(lambda a, b: a + b.get("text", ""), element.get("runs"), "")
    return element.get("simpleText", "")


def response(resp):
    results = []
    results_data = extr(resp.text, "ytInitialData = ", ";</script>")

    results_json = loads(results_data) if results_data else {}
    sections = (
        results_json.get("contents", {})
        .get("twoColumnSearchResultsRenderer", {})
        .get("primaryContents", {})
        .get("sectionListRenderer", {})
        .get("contents", [])
    )

    for section in sections:
        for video_container in (section.get("itemSectionRenderer") or {}).get("contents", []):
            video = video_container.get("videoRenderer") or {}
            videoid = video.get("videoId")
            if videoid is None:
                continue

            url = base_youtube_url + videoid
            thumbnail = "https://i.ytimg.com/vi/" + videoid + "/hqdefault.jpg"
            title = get_text_from_json(video.get("title", {}))
            content = get_text_from_json(video.get("descriptionSnippet", {}))
            author = get_text_from_json(video.get("ownerText", {}))
            length = get_text_from_json(video.get("lengthText", {}))

            results.append({
                "url": url,
                "title": title,
                "content": content,
                "author": author,
                "length": length,
                "template": "videos.html",
                "iframe_src": "https://www.youtube-nocookie.com/embed/" + videoid,
                "thumbnail": thumbnail,
            })

    return results
