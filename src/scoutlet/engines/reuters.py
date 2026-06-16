"""Reuters (news) - adapted from SearXNG.

Changes:
- Replaced dateutil.parser.isoparse with datetime.fromisoformat
"""

import logging
from json import dumps
from urllib.parse import quote_plus
from datetime import datetime, timedelta

logger = logging.getLogger("scoutlet.engines.reuters")

about = {
    "website": "https://www.reuters.com",
    "wikidata_id": "Q130879",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["news"]
time_range_support = True
paging = True

base_url = "https://www.reuters.com"
results_per_page = 20
sort_order = "relevance"

time_range_duration_map = {"day": 1, "week": 7, "month": 30, "year": 365}


def resize_url(thumbnail, width=0, height=0):
    url = (thumbnail or {}).get("resizer_url")
    if not url:
        return ""
    if int(width) > 0:
        url += f"&width={int(width)}"
    if int(height) > 0:
        url += f"&height={int(height)}"
    return url


def request(query, params):
    args = {
        "keyword": query,
        "offset": (params["pageno"] - 1) * results_per_page,
        "orderby": sort_order,
        "size": results_per_page,
        "website": "reuters",
    }
    if params.get("time_range"):
        time_diff_days = time_range_duration_map.get(params["time_range"], 0)
        if time_diff_days:
            start_date = datetime.now() - timedelta(days=time_diff_days)
            args["start_date"] = start_date.isoformat()

    params["url"] = f"{base_url}/pf/api/v3/content/fetch/articles-by-search-v2?query={quote_plus(dumps(args))}"
    return params


def response(resp):
    results = []
    resp_json = resp.json()

    if not resp_json.get("result"):
        return results

    for r in resp_json["result"].get("articles", []):
        publishedDate = None
        if r.get("display_time"):
            try:
                publishedDate = datetime.fromisoformat(r["display_time"].replace("Z", "+00:00"))
            except ValueError:
                pass

        results.append({
            "url": base_url + r.get("canonical_url", ""),
            "title": r.get("web", ""),
            "content": r.get("description", ""),
            "thumbnail": resize_url(r.get("thumbnail", {}), height=80),
            "metadata": (r.get("kicker") or {}).get("name"),
            "publishedDate": publishedDate,
        })

    return results
