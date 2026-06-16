"""GitHub repository search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced dateutil.parser with datetime.fromisoformat
"""

from datetime import datetime, timezone
from urllib.parse import urlencode

about = {
    "website": "https://github.com/",
    "wikidata_id": "Q364",
    "official_api_documentation": "https://developer.github.com/v3/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["it", "repos"]

search_url = "https://api.github.com/search/repositories?sort=stars&order=desc&{query}"
accept_header = "application/vnd.github.preview.text-match+json"


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def request(query, params):
    params["url"] = search_url.format(query=urlencode({"q": query}))
    params["headers"]["Accept"] = accept_header
    return params


def response(resp):
    results = []

    for item in resp.json().get("items", []):
        content = [item.get(i) for i in ["language", "description"] if item.get(i)]

        lic = item.get("license") or {}
        lic_url = None
        if lic.get("spdx_id"):
            lic_url = f"https://spdx.org/licenses/{lic.get('spdx_id')}.html"

        results.append(
            {
                "template": "packages.html",
                "url": item.get("html_url"),
                "title": item.get("full_name"),
                "content": " / ".join(content),
                "thumbnail": item.get("owner", {}).get("avatar_url"),
                "publishedDate": _parse_date(item.get("updated_at") or item.get("created_at")),
            }
        )

    return results
