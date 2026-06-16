"""MediathekViewWeb (videos) - adapted from SearXNG."""

import logging
import datetime
from json import loads, dumps

logger = logging.getLogger("scoutlet.engines.mediathekviewweb")

about = {
    "website": "https://mediathekviewweb.de/",
    "wikidata_id": "Q27877380",
    "official_api_documentation": "https://gist.github.com/bagbag/a2888478d27de0e989cf777f81fb33de",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
    "language": "de",
}

categories = ["videos"]
paging = True
time_range_support = False
safesearch = False


def request(query, params):
    params["url"] = "https://mediathekviewweb.de/api/query"
    params["method"] = "POST"
    params["headers"]["Content-type"] = "text/plain"
    params["data"] = dumps({
        "queries": [{"fields": ["title", "topic"], "query": query}],
        "sortBy": "timestamp",
        "sortOrder": "desc",
        "future": True,
        "offset": (params["pageno"] - 1) * 10,
        "size": 10,
    })
    return params


def response(resp):
    resp_data = loads(resp.text)
    mwv_result = resp_data.get("result", {})
    mwv_result_list = mwv_result.get("results", [])

    results = []
    for item in mwv_result_list:
        try:
            hms = str(datetime.timedelta(seconds=item.get("duration", 0)))
        except Exception:
            hms = ""

        url_hd = (item.get("url_video_hd") or "").replace("http://", "https://")
        results.append({
            "url": url_hd,
            "title": "%(channel)s: %(title)s (%(hms)s)" % {"channel": item.get("channel", ""), "title": item.get("title", ""), "hms": hms},
            "length": hms,
            "content": item.get("description", ""),
            "iframe_src": url_hd,
            "template": "videos.html",
        })

    return results
