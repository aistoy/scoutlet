"""Docker Hub image search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced dateutil.parser with datetime.fromisoformat
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
"""

import logging
from datetime import datetime
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.docker_hub")

about = {
    "website": "https://hub.docker.com/",
    "wikidata_id": "Q100294749",
    "official_api_documentation": "https://docs.docker.com/docker-hub/api/latest/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["it", "packages"]
paging = True

hub_url = "https://hub.docker.com/"
search_url = "https://hub.docker.com/v2/search/repositories/?{query}"


def request(query, params):
    args = urlencode({
        "query": query,
        "page": params["pageno"],
        "page_size": 25,
    })
    params["url"] = search_url.format(query=args)
    return params


def response(resp):
    results = []
    data = resp.json()

    for item in data.get("results", []):
        publishedDate = item.get("last_updated")
        if publishedDate:
            publishedDate = datetime.fromisoformat(publishedDate.replace("Z", "+00:00"))

        results.append({
            "template": "packages.html",
            "url": hub_url + "r/" + item.get("repo_name", ""),
            "title": item.get("repo_name", ""),
            "content": item.get("short_description", ""),
            "publishedDate": publishedDate,
            "thumbnail": item.get("logo_url", "").get("sm", "") if isinstance(item.get("logo_url"), dict) else item.get("logo_url", ""),
            "package_name": item.get("repo_name", ""),
            "maintainer": item.get("publisher", {}).get("name") if isinstance(item.get("publisher"), dict) else item.get("publisher", ""),
            "stars": item.get("star_count", 0),
            "source_code_url": item.get("repo_url", ""),
        })

    return results
