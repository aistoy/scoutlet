"""INA (videos) - adapted from SearXNG."""

import logging
from html import unescape
from urllib.parse import urlencode

from lxml import html

from scoutlet.utils import extract_text, eval_xpath, eval_xpath_list, eval_xpath_getindex

logger = logging.getLogger("scoutlet.engines.ina")

about = {
    "website": "https://www.ina.fr/",
    "wikidata_id": "Q1665109",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
    "language": "fr",
}

categories = ["videos"]
paging = True
page_size = 12

base_url = "https://www.ina.fr"
search_url = base_url + "/ajax/recherche?{query}&espace=1&sort=pertinence&order=desc&offset={start}&modified=size"

results_xpath = '//div[@id="searchHits"]/div'
url_xpath = ".//a/@href"
title_xpath = './/div[contains(@class,"title-bloc-small")]'
content_xpath = './/div[contains(@class,"sous-titre-fonction")]'
thumbnail_xpath = ".//img/@data-src"
publishedDate_xpath = './/div[contains(@class,"dateAgenda")]'


def request(query, params):
    params["url"] = search_url.format(start=params["pageno"] * page_size, query=urlencode({"q": query}))
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for result in eval_xpath_list(dom, results_xpath):
        url_relative = eval_xpath_getindex(result, url_xpath, 0, default="")
        url = base_url + (url_relative or "")
        title = unescape(extract_text(eval_xpath(result, title_xpath)) or "")
        thumbnail = extract_text(eval_xpath(result, thumbnail_xpath)) or ""
        content = (extract_text(eval_xpath(result, publishedDate_xpath)) or "") + (
            extract_text(eval_xpath(result, content_xpath)) or ""
        )

        results.append({
            "url": url,
            "title": title,
            "content": content,
            "template": "videos.html",
            "thumbnail": thumbnail,
        })

    return results
