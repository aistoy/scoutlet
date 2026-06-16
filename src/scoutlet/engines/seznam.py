"""Seznam search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced SearxEngineAccessDeniedException with SearchEngineAccessDeniedException
- from searx.network import get → from scoutlet.network import get
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
"""

import logging
from urllib.parse import urlencode

from lxml import html

from scoutlet.exceptions import SearchEngineAccessDeniedException
from scoutlet.network import get
from scoutlet.utils import (
    eval_xpath,
    eval_xpath_list,
    extract_text,
    extract_url,
)

logger = logging.getLogger("scoutlet.engines.seznam")

about = {
    "website": "https://www.seznam.cz/",
    "wikidata_id": "Q349048",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["general"]
paging = True

base_url = "https://search.seznam.cz"
search_url = "https://search.seznam.cz/?"


def request(query, params):
    args = urlencode({
        "q": query,
        "p": params["pageno"] - 1,  # Seznam is 0-indexed
    })
    params["url"] = search_url + args
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for result_el in eval_xpath_list(dom, '//div[contains(@class, "result")]', min_len=0):
        # Title and URL
        title_elem = eval_xpath(result_el, './/h3//a')
        if not title_elem:
            continue

        title = extract_text(title_elem)
        try:
            url = extract_url(eval_xpath(result_el, './/h3//a/@href'), base_url)
        except ValueError:
            continue

        # Description
        content_elem = eval_xpath(result_el, './/div[contains(@class,"description")]')
        content = extract_text(content_elem) if content_elem else ""

        if not title:
            continue

        results.append({
            "url": url,
            "title": title,
            "content": content,
        })

    return results
