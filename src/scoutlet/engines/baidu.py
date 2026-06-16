"""Baidu search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Removed fetch_traits (loaded from JSON)
"""

import logging
import time
import json
from urllib.parse import urlencode
from datetime import datetime
from html import unescape

from scoutlet.exceptions import SearchEngineAPIException, SearchEngineCaptchaException
from scoutlet.utils import html_to_text

logger = logging.getLogger("scoutlet.engines.baidu")

about = {
    "website": "https://www.baidu.com",
    "wikidata_id": "Q14772",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
    "language": "zh",
}

paging = True
categories = ["general"]
results_per_page = 10
baidu_category = 'general'
time_range_support = True
time_range_dict = {"day": 86400, "week": 604800, "month": 2592000, "year": 31536000}


def init(_):
    if baidu_category not in ('general', 'images', 'it'):
        raise SearchEngineAPIException(f"Unsupported category: {baidu_category}")


def request(query, params):
    page_num = params["pageno"]

    category_config = {
        'general': {
            'endpoint': 'https://www.baidu.com/s',
            'params': {
                "wd": query,
                "rn": results_per_page,
                "pn": (page_num - 1) * results_per_page,
                "tn": "json",
            },
        },
        'images': {
            'endpoint': 'https://image.baidu.com/search/acjson',
            'params': {
                "word": query,
                "rn": results_per_page,
                "pn": (page_num - 1) * results_per_page,
                "tn": "resultjson_com",
            },
        },
        'it': {
            'endpoint': 'https://kaifa.baidu.com/rest/v1/search',
            'params': {
                "wd": query,
                "pageSize": results_per_page,
                "pageNum": page_num,
                "paramList": f"page_num={page_num},page_size={results_per_page}",
                "position": 0,
            },
        },
    }

    query_params = category_config[baidu_category]['params']
    query_url = category_config[baidu_category]['endpoint']

    if params.get("time_range") in time_range_dict:
        now = int(time.time())
        past = now - time_range_dict[params["time_range"]]

        if baidu_category == 'general':
            query_params["gpc"] = f"stf={past},{now}|stftype=1"

        if baidu_category == 'it':
            query_params["paramList"] += f",timestamp_range={past}-{now}"

    params["url"] = f"{query_url}?{urlencode(query_params)}"
    params["allow_redirects"] = False
    return params


def response(resp):
    # Detect Baidu Captcha
    if 'wappass.baidu.com/static/captcha' in resp.headers.get('Location', ''):
        raise SearchEngineCaptchaException()

    text = resp.text
    if baidu_category == 'images':
        text = text.replace(r"\/", "/").replace(r"\'", "'")
    data = json.loads(text, strict=False)
    parsers = {'general': parse_general, 'images': parse_images, 'it': parse_it}

    return parsers[baidu_category](data)


def parse_general(data):
    results = []
    if not data.get("feed", {}).get("entry"):
        raise SearchEngineAPIException("Invalid response")

    for entry in data["feed"]["entry"]:
        if not entry.get("title") or not entry.get("url"):
            continue

        published_date = None
        if entry.get("time"):
            try:
                published_date = datetime.fromtimestamp(entry["time"])
            except (ValueError, TypeError):
                published_date = None

        title = unescape(entry["title"])
        content = unescape(entry.get("abs", ""))

        results.append({
            "title": title,
            "url": entry["url"],
            "content": content,
            "publishedDate": published_date,
        })
    return results


def parse_images(data):
    results = []
    if "data" in data:
        for item in data["data"]:
            if not item:
                continue
            replace_url = item.get("replaceUrl", [{}])[0]
            width = item.get("width")
            height = item.get("height")
            img_date = item.get("bdImgnewsDate")
            publishedDate = None
            if img_date:
                publishedDate = datetime.strptime(img_date, "%Y-%m-%d %H:%M")
            results.append({
                "template": "images.html",
                "url": replace_url.get("FromURL"),
                "thumbnail": item.get("thumbURL"),
                "img_src": replace_url.get("ObjURL"),
                "title": html_to_text(item.get("fromPageTitle")),
                "metadata": item.get("fromURLHost"),
            })
    return results


def parse_it(data):
    results = []
    if not data.get("data", {}).get("documents", {}).get("data"):
        raise SearchEngineAPIException("Invalid response")

    for entry in data["data"]["documents"]["data"]:
        results.append({
            'title': entry["techDocDigest"]["title"],
            'url': entry["techDocDigest"]["url"],
            'content': entry["techDocDigest"]["summary"],
        })
    return results
