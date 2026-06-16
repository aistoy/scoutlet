"""Deviantart - adapted from SearXNG.

Changes from SearXNG original:
- Removed engine_data nextpage pagination (use simple pageno)
"""

import logging
import urllib.parse

from lxml import html

from scoutlet.utils import extract_text, eval_xpath, eval_xpath_list

logger = logging.getLogger("scoutlet.engines.deviantart")

about = {
    "website": "https://www.deviantart.com/",
    "wikidata_id": "Q46523",
    "official_api_documentation": "https://www.deviantart.com/developers/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["images"]
paging = True

base_url = "https://www.deviantart.com"

results_xpath = '//div[@class="V_S0t_"]/div/div/a'
url_xpath = "./@href"
thumbnail_src_xpath = "./div/img/@src"
img_src_xpath = "./div/img/@srcset"
title_xpath = "./@aria-label"
premium_xpath = "../div/div/div/text()"
premium_keytext = "Watch the artist to view this deviation"


def request(query, params):
    page = params.get("pageno", 1)
    params["url"] = f"{base_url}/search?{urllib.parse.urlencode({'q': query})}&page={page}"
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for result in eval_xpath_list(dom, results_xpath):
        _text = extract_text(eval_xpath(result, premium_xpath))
        if _text and premium_keytext in _text:
            continue
        img_src = extract_text(eval_xpath(result, img_src_xpath))
        if img_src:
            img_src = img_src.split(" ")[0]
            parsed_url = urllib.parse.urlparse(img_src)
            img_src = parsed_url._replace(path=parsed_url.path.split("/v1")[0]).geturl()

        results.append({
            "template": "images.html",
            "url": extract_text(eval_xpath(result, url_xpath)),
            "img_src": img_src,
            "thumbnail_src": extract_text(eval_xpath(result, thumbnail_src_xpath)),
            "title": extract_text(eval_xpath(result, title_xpath)),
        })

    return results
