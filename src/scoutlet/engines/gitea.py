"""Gitea / Forgejo instance search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced dateutil.parser with datetime.fromisoformat
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
"""

import logging
from datetime import datetime
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.gitea")

about = {
    "website": "https://about.gitea.com/",
    "wikidata_id": "Q28602451",
    "official_api_documentation": "https://docs.gitea.io/en-us/api-usage/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["it", "repos"]
paging = True

# Default instance; can be overridden in settings
base_url = "https://codeberg.org"
search_url = "{base_url}/api/v1/repos/search?{query}"


def request(query, params):
    args = urlencode({
        "q": query,
        "page": params["pageno"],
        "limit": 10,
        "sort": "updated",
    })
    params["url"] = search_url.format(base_url=base_url, query=args)
    return params


def response(resp):
    results = []
    data = resp.json()

    for item in data.get("data", []):
        publishedDate = None
        updated_at = item.get("updated_at")
        if updated_at:
            try:
                publishedDate = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        content_parts = []
        if item.get("description"):
            content_parts.append(item["description"])
        if item.get("language"):
            content_parts.append(item["language"])
        if item.get("stars_count"):
            content_parts.append(f"stars: {item['stars_count']}")
        if item.get("forks_count"):
            content_parts.append(f"forks: {item['forks_count']}")

        results.append({
            "template": "packages.html",
            "url": item.get("html_url", ""),
            "title": item.get("full_name") or item.get("name", ""),
            "content": " | ".join(content_parts),
            "publishedDate": publishedDate,
            "thumbnail": item.get("owner", {}).get("avatar_url", ""),
            "stars": item.get("stars_count", 0),
            "forks": item.get("forks_count", 0),
            "source_code_url": item.get("html_url", ""),
        })

    return results
