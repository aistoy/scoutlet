"""Pixiv - adapted from SearXNG."""

import logging
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.pixiv")

about = {
    "website": "https://www.pixiv.net/",
    "wikidata_id": "Q306956",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

paging = True
categories = ["images"]
remove_ai_images = False

base_url = "https://www.pixiv.net/ajax/search/illustrations"
pixiv_image_proxies: list = []


def request(query, params):
    query_params = {
        "word": query,
        "order": "date_d",
        "mode": "all",
        "p": params["pageno"],
        "s_mode": "s_tag_full",
        "type": "illust_and_ugoira",
        "lang": "en",
    }
    if remove_ai_images:
        query_params["ai_type"] = 1

    params["url"] = f"{base_url}/{query}?{urlencode(query_params)}"
    return params


def response(resp):
    results = []
    data = resp.json()

    body = data.get("body") or {}
    illust = body.get("illust") or {}
    items = illust.get("data") or []

    for item in items:
        image_url = item.get("url", "")
        if pixiv_image_proxies:
            import random
            pixiv_proxy = random.choice(pixiv_image_proxies)
            proxy_image_url = image_url.replace("https://i.pximg.net", pixiv_proxy)
            proxy_full_image_url = (
                proxy_image_url.replace("/c/250x250_80_a2/", "/")
                .replace("_square1200.jpg", "_master1200.jpg")
                .replace("custom-thumb", "img-master")
                .replace("_custom1200.jpg", "_master1200.jpg")
            )
        else:
            proxy_image_url = image_url
            proxy_full_image_url = image_url

        results.append({
            "title": item.get("title"),
            "url": proxy_full_image_url,
            "content": item.get("alt"),
            "author": "%s (ID: %s)" % (item.get("userName", ""), item.get("userId", "")),
            "img_src": proxy_full_image_url,
            "thumbnail_src": proxy_image_url,
            "source": "pixiv.net",
            "template": "images.html",
        })

    return results
