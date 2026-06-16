"""Moviepilot (movies) - adapted from SearXNG.

Changes:
- Stored 'discovery' flag on params dict instead of resp.search_params (which
  scoutlet doesn't populate)
"""

import logging
from urllib.parse import urlencode

from scoutlet.utils import html_to_text

logger = logging.getLogger("scoutlet.engines.moviepilot")

about = {
    "website": "https://www.moviepilot.de",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
    "language": "de",
}

paging = True
categories = ["movies"]

base_url = "https://www.moviepilot.de"
image_url_template = "https://assets.cdn.moviepilot.de/files/{image_id}/fill/155/223/{filename}"

filter_types = ["fsk", "genre", "jahr", "jahrzehnt", "land", "online", "stimmung", "person"]


def request(query, params):
    query_parts = query.split(" ")
    discovery_filters = []
    for query_part in query_parts:
        filter_category_and_value = query_part.split("-", 1)
        if len(filter_category_and_value) < 2:
            continue
        if filter_category_and_value[0] in filter_types:
            discovery_filters.append(query_part)

    is_discovery = len(discovery_filters) != 0
    # Stash on params so response() can read it back
    params["moviepilot_discovery"] = is_discovery

    if is_discovery:
        args = {"page": params["pageno"], "order": "beste"}
        params["url"] = f"{base_url}/api/discovery?{urlencode(args)}"
        for f in discovery_filters:
            params["url"] += f"&filters[]={f}"
    else:
        args = {"q": query, "page": params["pageno"], "type": "suggest"}
        params["url"] = f"{base_url}/api/search?{urlencode(args)}"

    return params


def response(resp):
    results = []
    json_data = resp.json()
    is_discovery = getattr(resp, "search_params", {}).get("moviepilot_discovery") or \
        (resp.url.find("/api/discovery") != -1)

    json_results = json_data.get("results", []) if is_discovery else json_data

    for result in json_results:
        item = {"title": result.get("title", "")}

        if is_discovery:
            content_list = [result.get(x) for x in ["abstract", "summary"]]
            item["url"] = base_url + result.get("path", "")
            item["content"] = html_to_text(" | ".join([x for x in content_list if x]))
            item["metadata"] = html_to_text(result.get("meta_short", ""))

            if result.get("image"):
                item["thumbnail"] = image_url_template.format(
                    image_id=result["image"], filename=result.get("image_filename", "")
                )
        else:
            item["url"] = result.get("url", "")
            item["content"] = ", ".join([
                str(result.get("class", "")),
                str(result.get("info", "")),
                str(result.get("more", "")),
            ])
            item["thumbnail"] = result.get("image")

        results.append(item)

    return results
