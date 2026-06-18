"""Emojipedia - adapted from SearXNG.

SearXNG upstream leaves categories empty so the engine only fires when
explicitly invoked. Scoutlet places it under "general" so it shows up in
--list-engines --by-category; users wanting to skip it can pass -e explicitly.
"""

import logging
from urllib.parse import urlencode

from lxml import html

from scoutlet.utils import eval_xpath_list, extract_text

logger = logging.getLogger("scoutlet.engines.emojipedia")

about = {
    "website": "https://emojipedia.org",
    "wikidata_id": "Q22908129",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = []

base_url = "https://emojipedia.org"
search_url = base_url + "/search?{query}"


def request(query, params):
    params["url"] = search_url.format(query=urlencode({"q": query}))
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for result in eval_xpath_list(dom, '//div[starts-with(@class, "EmojisList")]/a'):
        url = base_url + (result.attrib.get("href") or "")
        results.append({
            "url": url,
            "title": extract_text(result) or "",
            "content": "",
        })

    return results
