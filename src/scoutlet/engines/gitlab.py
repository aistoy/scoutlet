"""GitLab project search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced dateutil.parser with datetime.fromisoformat

Configuration:
    base_url must be set via engine_configs, e.g.:
        load_engines(engine_configs={"gitlab": {"base_url": "https://gitlab.com"}})
"""

from datetime import datetime, timezone
from urllib.parse import urlencode

about = {
    "website": None,
    "wikidata_id": None,
    "official_api_documentation": "https://docs.gitlab.com/ee/api/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["it", "repos"]
paging = True

base_url: str = "https://gitlab.com"
api_path: str = "api/v4/projects"


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
    args = {"search": query, "page": params["pageno"]}
    params["url"] = f"{base_url}/{api_path}?{urlencode(args)}"
    return params


def response(resp):
    results = []

    for item in resp.json():
        results.append(
            {
                "template": "packages.html",
                "url": item.get("web_url"),
                "title": item.get("name"),
                "content": item.get("description"),
                "thumbnail": item.get("avatar_url"),
                "publishedDate": _parse_date(
                    item.get("last_activity_at") or item.get("created_at")
                ),
            }
        )

    return results
