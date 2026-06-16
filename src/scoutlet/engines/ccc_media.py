"""media.ccc.de - adapted from SearXNG.

Changes:
- Replaced dateutil.parser with datetime.fromisoformat
"""

import logging
import datetime
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.ccc_media")

about = {
    "website": "https://media.ccc.de",
    "official_api_documentation": "https://github.com/voc/voctoweb",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["videos"]
paging = True

api_url = "https://api.media.ccc.de"


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def request(query, params):
    args = {"q": query, "page": params["pageno"]}
    params["url"] = f"{api_url}/public/events/search?{urlencode(args)}"
    return params


def response(resp):
    results = []

    for item in resp.json().get("events", []):
        publishedDate = _parse_date(item.get("date"))

        iframe_src = None
        for rec in item.get("recordings", []):
            mime = rec.get("mime_type", "")
            if mime.startswith("video"):
                if not iframe_src:
                    iframe_src = rec.get("recording_url")
                elif mime == "video/mp4":
                    iframe_src = rec.get("recording_url")

        results.append({
            "template": "videos.html",
            "url": item.get("frontend_link", ""),
            "title": item.get("title", ""),
            "content": item.get("description", ""),
            "thumbnail": item.get("thumb_url", ""),
            "publishedDate": publishedDate,
            "length": datetime.timedelta(seconds=item.get("length", 0)),
            "iframe_src": iframe_src,
        })

    return results
