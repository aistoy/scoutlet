"""SourceHut git repository search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced searxng_useragent() with gen_useragent()
- Replaced res.types.LegacyResult with plain dicts
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
"""

import logging
from urllib.parse import urlencode

from scoutlet.utils import gen_useragent

logger = logging.getLogger("scoutlet.engines.sourcehut")

about = {
    "website": "https://sr.ht/",
    "wikidata_id": "Q78553966",
    "official_api_documentation": "https://man.sr.ht/graphql.md",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["it", "repos"]
paging = True

search_url = "https://sr.ht/api/repos?"


def request(query, params):
    args = urlencode({
        "search": query,
        "page": params["pageno"],
    })
    params["url"] = search_url + args
    params["headers"]["User-Agent"] = gen_useragent()
    return params


def response(resp):
    results = []
    data = resp.json()

    # API returns a dict with "results" list or a list directly
    items = data
    if isinstance(data, dict):
        items = data.get("results", [])

    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name", "")
        owner = item.get("owner", {})
        if isinstance(owner, dict):
            owner_name = owner.get("canonical_name", owner.get("name", ""))
        else:
            owner_name = str(owner)

        url = item.get("html_url", f"https://sr.ht/~{owner_name}/{name}")
        description = item.get("description", "")

        content_parts = []
        if description:
            content_parts.append(description)
        visibility = item.get("visibility", "")
        if visibility:
            content_parts.append(f"visibility: {visibility}")

        results.append({
            "url": url,
            "title": f"~{owner_name}/{name}" if owner_name else name,
            "content": " | ".join(content_parts),
        })

    return results
