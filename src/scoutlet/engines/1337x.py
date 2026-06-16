"""1337x torrent search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
- Removed fetch_traits()
"""

import logging
from urllib.parse import urljoin

from lxml import html

from scoutlet.utils import (
    eval_xpath,
    eval_xpath_getindex,
    eval_xpath_list,
    extract_text,
    extract_url,
)

logger = logging.getLogger("scoutlet.engines.1337x")

about = {
    "website": "https://1337x.to/",
    "wikidata_id": "Q55358384",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["files"]
paging = True

base_url = "https://1337x.to"
search_url = "/search/{query}/{pageno}/"

# XPath selectors for the torrent table
_xpath_torrent_row = './/table[contains(@class, "table-list")]//tr'
_xpath_title = './/td[contains(@class, "name")]//a[last()]'
_xpath_url = './/td[contains(@class, "name")]//a[last()]/@href'
_xpath_seeders = './/td[contains(@class, "seeds")]'
_xpath_leechers = './/td[contains(@class, "leeches")]'
_xpath_date = './/td[contains(@class, "coll-date")]'
_xpath_size = './/td[contains(@class, "size")]'  # note: contains "size" and uploader


def request(query, params):
    params["url"] = urljoin(base_url, search_url.format(
        query=query.replace(" ", "+"),
        pageno=params["pageno"],
    ))
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for row in eval_xpath_list(dom, _xpath_torrent_row, min_len=0):
        # Title and URL
        title = extract_text(eval_xpath(row, _xpath_title))
        try:
            url = extract_url(eval_xpath(row, _xpath_url), base_url)
        except ValueError:
            continue

        # Seeders / Leechers
        seeders = extract_text(eval_xpath(row, _xpath_seeders))
        leechers = extract_text(eval_xpath(row, _xpath_leechers))

        # Date
        date_str = extract_text(eval_xpath(row, _xpath_date))

        # Size (text also contains the uploader name, we want only the size part)
        size_text = extract_text(eval_xpath(row, _xpath_size))

        content_parts = []
        if size_text:
            # Size cell has format "size uploader" - take first token group
            import re
            size_match = re.match(r'([\d.]+\s*[KMGT]?B)', size_text)
            if size_match:
                content_parts.append(size_match.group(1))
        if seeders:
            content_parts.append("Seeders: " + seeders)
        if leechers:
            content_parts.append("Leechers: " + leechers)

        results.append({
            "url": url,
            "title": title or "",
            "content": " | ".join(content_parts),
            "seed": seeders,
            "leech": leechers,
            "template": "torrent.html",
        })

    return results
