"""Ansa (Italian news agency) - adapted from SearXNG."""

import logging
from urllib.parse import urlencode

from lxml import html

from scoutlet.utils import eval_xpath, eval_xpath_list, extract_text

logger = logging.getLogger("scoutlet.engines.ansa")

about = {
    "website": "https://www.ansa.it",
    "wikidata_id": "Q392934",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
    "language": "it",
}

categories = ["news"]
paging = True
page_size = 12
base_url = "https://www.ansa.it"

time_range_support = True
time_range_args = {"day": 1, "week": 7, "month": 31, "year": 365}

search_api = "https://www.ansa.it/ricerca/ansait/search.shtml?"


def request(query, params):
    query_params = {
        "any": query,
        "start": (params["pageno"] - 1) * page_size,
        "sort": "data:desc",
    }
    if params.get("time_range"):
        query_params["periodo"] = time_range_args.get(params["time_range"])

    params["url"] = search_api + urlencode(query_params)
    return params


def response(resp):
    results = []
    doc = html.fromstring(resp.text)

    for result in eval_xpath_list(doc, "//div[@class='article']"):
        url = base_url + (extract_text(eval_xpath(result, "./div[@class='content']/h2[@class='title']/a/@href")) or "")
        item = {
            "title": extract_text(eval_xpath(result, "./div[@class='content']/h2[@class='title']/a")) or "",
            "content": extract_text(eval_xpath(result, "./div[@class='content']/div[@class='text']")) or "",
            "url": url,
        }
        thumbnail = extract_text(eval_xpath(result, "./div[@class='image']/a/img/@src")) or ""
        if thumbnail:
            item["thumbnail"] = base_url + thumbnail
        results.append(item)

    return results
