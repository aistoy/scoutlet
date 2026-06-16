"""Vimeo video search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced dateutil.parser with datetime.fromisoformat
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
- Removed fetch_traits()
"""

import logging
from datetime import datetime
from urllib.parse import urlencode

from scoutlet.utils import extr

logger = logging.getLogger("scoutlet.engines.vimeo")

about = {
    "website": "https://vimeo.com/",
    "wikidata_id": "Q156905",
    "official_api_documentation": "https://developer.vimeo.com/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["videos"]
paging = True

search_url = "https://vimeo.com/search?{query}"


def request(query, params):
    args = urlencode({"q": query, "page": params["pageno"]})
    params["url"] = search_url.format(query=args)
    return params


def response(resp):
    results = []
    html_text = resp.text

    # Vimeo embeds video data in JSON inside the page HTML
    json_data = extr(html_text, "const clips = ", ";\n")
    if not json_data:
        # Try alternate pattern
        json_data = extr(html_text, '"filtered":', ',"_headers"')
        if json_data:
            json_data = "{" + '"filtered":' + json_data + "}"

    if not json_data:
        return results

    import json
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError:
        return results

    # Navigate the JSON structure
    clips = data
    if isinstance(data, dict):
        clips = data.get("filtered", data.get("data", data.get("clips", [])))
        if isinstance(clips, dict):
            clips = clips.get("data", [])

    if not isinstance(clips, list):
        return results

    for clip in clips:
        if not isinstance(clip, dict):
            continue

        publishedDate = None
        release_time = clip.get("release_time") or clip.get("created_time")
        if release_time:
            try:
                publishedDate = datetime.fromisoformat(release_time.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        thumbnail = clip.get("pictures", {})
        if isinstance(thumbnail, dict):
            sizes = thumbnail.get("sizes", [])
            thumbnail = sizes[-1]["link"] if sizes else ""
        elif not isinstance(thumbnail, str):
            thumbnail = ""

        results.append({
            "url": clip.get("link", clip.get("uri", "")),
            "title": clip.get("name", ""),
            "content": clip.get("description", ""),
            "publishedDate": publishedDate,
            "thumbnail": thumbnail,
            "template": "videos.html",
        })

    return results
