"""FindThatMeme - adapted from SearXNG.

Changes:
- Replaced humanize_bytes with local formatter
- Replaced dateutil with datetime.fromisoformat
"""

import logging
from json import dumps
from datetime import datetime

logger = logging.getLogger("scoutlet.engines.findthatmeme")

about = {
    "website": "https://findthatmeme.com",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

base_url = "https://findthatmeme.com/api/v1/search"
categories = ["images"]
paging = True


def _humanize_bytes(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TB"


def request(query, params):
    start_index = (params["pageno"] - 1) * 50
    data = {"search": query, "offset": start_index}
    params["url"] = base_url
    params["method"] = "POST"
    params["headers"]["content-type"] = "application/json"
    params["data"] = dumps(data)
    return params


def response(resp):
    search_res = resp.json()
    results = []

    for item in search_res:
        img = "https://s3.thehackerblog.com/findthatmeme/" + item.get("image_path", "")
        thumb = "https://s3.thehackerblog.com/findthatmeme/thumb/" + item.get("thumbnail", "")
        publishedDate = None
        updated_at = item.get("updated_at")
        if updated_at:
            try:
                publishedDate = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except ValueError:
                try:
                    publishedDate = datetime.strptime(updated_at.split("T")[0], "%Y-%m-%d")
                except ValueError:
                    pass

        results.append({
            "url": item.get("source_page_url"),
            "title": item.get("source_site"),
            "img_src": img if item.get("type") == "IMAGE" else thumb,
            "filesize": _humanize_bytes(item.get("meme_file_size", 0)),
            "publishedDate": publishedDate,
            "template": "images.html",
        })

    return results
