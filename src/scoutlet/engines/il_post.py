"""Il Post (Italian news) - adapted from SearXNG."""

import logging
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.il_post")

about = {
    "website": "https://www.ilpost.it",
    "wikidata_id": "Q3792882",
    "official_api_documentation": None,
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
    "language": "it",
}

categories = ["news"]
paging = True
page_size = 10

time_range_support = True
time_range_args = {"month": "pub_date:ultimi_30_giorni", "year": "pub_date:ultimo_anno"}

search_api = "https://api.ilpost.org/search/api/site_search/?"


def request(query, params):
    query_params = {
        "qs": query,
        "pg": params["pageno"],
        "sort": "date_d",
        "filters": "ctype:articoli",
    }
    if params.get("time_range"):
        if params["time_range"] not in time_range_args:
            return None
        query_params["filters"] += f";{time_range_args.get(params['time_range'], 'pub_date:da_sempre')}"
    params["url"] = search_api + urlencode(query_params)
    return params


def response(resp):
    results = []
    json_data = resp.json()

    for result in json_data.get("docs", []):
        results.append({
            "url": result.get("link", ""),
            "title": result.get("title", ""),
            "content": result.get("summary", ""),
            "thumbnail": result.get("image"),
        })

    return results
