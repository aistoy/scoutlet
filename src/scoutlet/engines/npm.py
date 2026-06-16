"""NPM package search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced dateutil.parser with datetime.fromisoformat
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
"""

import logging
from urllib.parse import urlencode
from datetime import datetime

logger = logging.getLogger("scoutlet.engines.npm")

about = {
    "website": "https://npms.io/",
    "wikidata_id": "Q7067518",
    "official_api_documentation": "https://api-docs.npms.io/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

categories = ['it', 'packages']
paging = True
page_size = 25
search_api = "https://api.npms.io/v2/search?"


def request(query, params):
    args = urlencode({
        'from': (params["pageno"] - 1) * page_size,
        'q': query,
        'size': page_size,
    })
    params['url'] = search_api + args
    return params


def response(resp):
    results = []
    content = resp.json()
    for entry in content.get("results", []):
        package = entry["package"]
        publishedDate = package.get("date")
        if publishedDate:
            publishedDate = datetime.fromisoformat(publishedDate.replace("Z", "+00:00"))
        tags = list(entry.get("flags", {}).keys()) + package.get("keywords", [])
        results.append({
            "template": "packages.html",
            "url": package["links"]["npm"],
            "title": package["name"],
            'package_name': package["name"],
            "content": package.get("description", ""),
            "version": package.get("version"),
            "maintainer": package.get("author", {}).get("name"),
            'publishedDate': publishedDate,
            "tags": tags,
            "homepage": package["links"].get("homepage"),
            "source_code_url": package["links"].get("repository"),
        })
    return results
