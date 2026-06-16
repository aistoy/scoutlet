"""ScanR Structures (French research institutions) - adapted from SearXNG.

Changes from SearXNG original:
- from searx.utils.html_to_text -> from scoutlet.utils.html_to_text
"""

import logging
from json import loads, dumps

from scoutlet.utils import html_to_text

logger = logging.getLogger("scoutlet.engines.scanr_structures")

about = {
    "website": "https://scanr.enseignementsup-recherche.gouv.fr",
    "wikidata_id": "Q44105684",
    "official_api_documentation": "https://scanr.enseignementsup-recherche.gouv.fr/opendata",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["science"]
paging = True
page_size = 20

url = "https://scanr.enseignementsup-recherche.gouv.fr/"
search_url = url + "api/structures/search"


def request(query, params):
    params["url"] = search_url
    params["method"] = "POST"
    params["headers"]["Content-type"] = "application/json"
    params["data"] = dumps({
        "query": query,
        "searchField": "ALL",
        "sortDirection": "ASC",
        "sortOrder": "RELEVANCY",
        "page": params["pageno"],
        "pageSize": page_size,
    })
    return params


def response(resp):
    results = []
    search_res = loads(resp.text)

    if search_res.get("total", 0) < 1:
        return []

    for result in search_res.get("results", []):
        if "id" not in result:
            continue

        thumbnail = None
        if "logo" in result:
            thumbnail = result["logo"]
            if thumbnail and thumbnail[0] == "/":
                thumbnail = url + thumbnail

        content = None
        if "highlights" in result:
            highlights = result["highlights"]
            if highlights:
                content = highlights[0].get("value")

        results.append({
            "url": url + "structure/" + result["id"],
            "title": result.get("label", ""),
            "thumbnail": thumbnail,
            "content": html_to_text(content) if content else "",
        })

    return results
