"""Crates.io (Rust) package search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced dateutil.parser with datetime.fromisoformat
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
"""

import logging
from datetime import datetime
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.crates")

about = {
    "website": "https://crates.io/",
    "wikidata_id": "Q42969546",
    "official_api_documentation": "https://crates.io/data-access",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["it", "packages"]
paging = True

search_url = "https://crates.io/api/v1/crates?{query}"


def request(query, params):
    args = urlencode({
        "q": query,
        "page": params["pageno"],
    })
    params["url"] = search_url.format(query=args)
    params["headers"]["Accept"] = "application/json"
    return params


def response(resp):
    results = []
    data = resp.json()

    for item in data.get("crates", []):
        publishedDate = item.get("updated_at")
        if publishedDate:
            publishedDate = datetime.fromisoformat(publishedDate.replace("Z", "+00:00"))

        content_parts = []
        if item.get("description"):
            content_parts.append(item["description"])
        if item.get("max_version"):
            content_parts.append("v" + item["max_version"])
        if item.get("downloads"):
            content_parts.append("downloads: " + str(item["downloads"]))

        results.append({
            "template": "packages.html",
            "url": "https://crates.io/crates/" + item.get("name", ""),
            "title": item.get("name", ""),
            "content": " | ".join(content_parts),
            "publishedDate": publishedDate,
            "package_name": item.get("name", ""),
            "version": item.get("max_version"),
            "homepage": item.get("homepage"),
            "source_code_url": item.get("repository"),
        })

    return results
