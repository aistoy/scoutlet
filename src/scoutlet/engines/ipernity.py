"""Ipernity (images) - adapted from SearXNG."""

import logging
from datetime import datetime
from json import loads, JSONDecodeError
from urllib.parse import quote_plus

from lxml import html

from scoutlet.utils import extr, extract_text, eval_xpath, eval_xpath_list

logger = logging.getLogger("scoutlet.engines.ipernity")

about = {
    "website": "https://www.ipernity.com",
    "official_api_documentation": "https://www.ipernity.com/help/api",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

paging = True
categories = ["images"]

base_url = "https://www.ipernity.com"
page_size = 10


def request(query, params):
    params["url"] = f"{base_url}/search/photo/@/page:{params['pageno']}:{page_size}?q={quote_plus(query)}"
    return params


def response(resp):
    results = []
    doc = html.fromstring(resp.text)

    images = eval_xpath_list(doc, '//a[starts-with(@href, "/doc")]//img')

    result_index = 0
    for result in eval_xpath_list(doc, '//script[@type="text/javascript"]'):
        info_js = extr(extract_text(result), "] = ", "};") + "}"

        if not info_js:
            continue

        try:
            info_item = loads(info_js)

            if not info_item.get("mediakey"):
                continue

            if result_index >= len(images):
                break
            thumbnail_src = extract_text(eval_xpath(images[result_index], "./@src")) or ""
            img_src = thumbnail_src.replace("240.jpg", "640.jpg")

            resolution = None
            if info_item.get("width") and info_item.get("height"):
                resolution = f"{info_item['width']}x{info_item['height']}"

            publishedDate = None
            posted_at = info_item.get("posted_at")
            if posted_at:
                try:
                    publishedDate = datetime.fromtimestamp(int(posted_at))
                except (ValueError, TypeError):
                    pass

            item = {
                "template": "images.html",
                "url": f"{base_url}/doc/{info_item.get('user_id', '')}/{info_item.get('doc_id', '')}",
                "title": info_item.get("title"),
                "content": info_item.get("content", ""),
                "resolution": resolution,
                "publishedDate": publishedDate,
                "thumbnail_src": thumbnail_src,
                "img_src": img_src,
            }
            results.append(item)

            result_index += 1
        except JSONDecodeError:
            continue

    return results
