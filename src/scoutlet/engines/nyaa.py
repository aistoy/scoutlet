"""Nyaa.si torrent search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
"""

import logging
from urllib.parse import urlencode

from lxml import html

from scoutlet.utils import (
    eval_xpath,
    eval_xpath_list,
    extract_text,
    extract_url,
)

logger = logging.getLogger("scoutlet.engines.nyaa")

about = {
    "website": "https://nyaa.si/",
    "wikidata_id": None,
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["files"]
paging = True

base_url = "https://nyaa.si"
search_url = "https://nyaa.si/?{query}"


def request(query, params):
    args = urlencode({
        "q": query,
        "p": params["pageno"],
    })
    params["url"] = search_url.format(query=args)
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for row in eval_xpath_list(dom, '//table[contains(@class,"torrent-list")]//tr', min_len=0):
        # Skip table header rows
        tds = eval_xpath_list(row, './td', min_len=0)
        if len(tds) < 6:
            continue

        # Title: links in the second td
        links = eval_xpath_list(tds[1], './/a', min_len=0)
        if not links:
            continue

        title = extract_text(links[-1])
        try:
            url = extract_url([links[-1]], base_url)
        except ValueError:
            continue

        # Magnet link
        magnet_link = ""
        magnet_elem = eval_xpath(tds[2], './/a[contains(@href,"magnet:")]/@href')
        if magnet_elem:
            magnet_link = magnet_elem[0] if isinstance(magnet_elem, list) else magnet_elem

        # Size
        size = extract_text(tds[3]) if len(tds) > 3 else ""

        # Date
        date_str = extract_text(tds[4]) if len(tds) > 4 else ""

        # Seeders / Leechers
        seeders = extract_text(tds[5]) if len(tds) > 5 else "0"
        leechers = extract_text(tds[6]) if len(tds) > 6 else "0"

        content_parts = []
        if size:
            content_parts.append(size)
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
            "filesize": size,
            "magnetlink": magnet_link,
            "template": "torrent.html",
        })

    return results
