"""Tootfinder (social media) - adapted from SearXNG."""

import logging
from datetime import datetime
from json import loads

from scoutlet.utils import html_to_text

logger = logging.getLogger("scoutlet.engines.tootfinder")

about = {
    "website": "https://www.tootfinder.ch",
    "official_api_documentation": "https://wiki.tootfinder.ch/index.php?name=the-tootfinder-rest-api",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["social media"]

base_url = "https://www.tootfinder.ch"


def request(query, params):
    params["url"] = f"{base_url}/rest/api/search/{query}"
    return params


def response(resp):
    results = []
    json_str = ""
    # API sometimes appends HTML error after the JSON line
    for line in resp.text.split("\n"):
        if line.startswith("[{"):
            json_str = line
            break

    if not json_str:
        return results

    for result in loads(json_str):
        thumbnail = None
        attachments = result.get("media_attachments", []) or []
        images = [a["preview_url"] for a in attachments if a.get("type") == "image" and a.get("preview_url")]
        if images:
            thumbnail = images[0]

        card = result.get("card") or {}
        title = card.get("title")
        if not title:
            title = html_to_text(result.get("content", ""))[:75]

        publishedDate = None
        if result.get("created_at"):
            try:
                publishedDate = datetime.strptime(result["created_at"], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        results.append({
            "url": result.get("url", ""),
            "title": title,
            "content": html_to_text(result.get("content", "")),
            "thumbnail": thumbnail,
            "publishedDate": publishedDate,
        })

    return results
