"""Bilibili video search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Added WBI signature for search API (B站 2023+ requires signed requests)
"""

import hashlib
import time
import logging
from urllib.parse import urlencode
from datetime import datetime, timedelta

from scoutlet.utils import html_to_text, parse_duration_string
from scoutlet.network import get as http_get

logger = logging.getLogger("scoutlet.engines.bilibili")

about = {
    "website": "https://www.bilibili.com",
    "wikidata_id": "Q3077586",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

paging = True
results_per_page = 20
categories = ["videos"]

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA, "Referer": "https://www.bilibili.com"}

# WBI mixin key reordering table
_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]

# Cached WBI keys
_wbi_keys: dict | None = None
_wbi_keys_ts: float = 0


def _get_mixin_key(orig: str) -> str:
    return "".join(orig[i] for i in _MIXIN_KEY_ENC_TAB)[:32]


def _get_wbi_keys() -> tuple[str, str] | None:
    global _wbi_keys, _wbi_keys_ts
    # Cache for 10 minutes
    if _wbi_keys and time.time() - _wbi_keys_ts < 600:
        return _wbi_keys["img_key"], _wbi_keys["sub_key"]
    try:
        resp = http_get(
            "https://api.bilibili.com/x/web-interface/nav",
            headers=_HEADERS, timeout=5,
        )
        data = resp.json().get("data", {}).get("wbi_img", {})
        img_key = data.get("img_url", "").split("/")[-1].split(".")[0]
        sub_key = data.get("sub_url", "").split("/")[-1].split(".")[0]
        if img_key and sub_key:
            _wbi_keys = {"img_key": img_key, "sub_key": sub_key}
            _wbi_keys_ts = time.time()
            return img_key, sub_key
    except Exception:
        logger.warning("Failed to fetch WBI keys")
    return None


def _sign_wbi(params: dict, img_key: str, sub_key: str) -> dict:
    mixin_key = _get_mixin_key(img_key + sub_key)
    params["wts"] = int(time.time())
    params = {k: v for k, v in sorted(params.items()) if v is not None and v != ""}
    query = urlencode(params)
    params["w_rid"] = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return params


def request(query, params):
    query_params = {
        "keyword": query,
        "search_type": "video",
        "page": params["pageno"],
        "page_size": results_per_page,
    }

    keys = _get_wbi_keys()
    if keys:
        img_key, sub_key = keys
        signed = _sign_wbi(query_params, img_key, sub_key)
        params["url"] = "https://api.bilibili.com/x/web-interface/wbi/search/type?" + urlencode(signed)
    else:
        # Fallback to unsigned API
        params["url"] = "https://api.bilibili.com/x/web-interface/search/type?" + urlencode(query_params)

    params["headers"].update(_HEADERS)
    return params


def response(resp):
    try:
        search_res = resp.json()
    except Exception:
        return []

    if search_res.get("code") != 0:
        logger.warning("Bilibili API error: %s", search_res.get("message", "unknown"))
        return []

    results = []
    for item in search_res.get("data", {}).get("result", []):
        title = html_to_text(item.get("title", ""))
        url = item.get("arcurl", "")
        if not title or not url:
            continue

        thumbnail = item.get("pic", "")
        if thumbnail and not thumbnail.startswith("http"):
            thumbnail = "https:" + thumbnail

        video_id = item.get("aid")
        iframe_url = f"https://player.bilibili.com/player.html?aid={video_id}&high_quality=1&autoplay=false&danmaku=0" if video_id else ""

        unix_date = item.get("pubdate")
        publishedDate = datetime.fromtimestamp(unix_date) if unix_date else None

        duration = parse_duration_string(item.get("duration", ""))
        if duration and duration > timedelta(minutes=60):
            duration = None

        results.append({
            "title": title,
            "url": url,
            "content": item.get("description", ""),
            "author": item.get("author", ""),
            "publishedDate": publishedDate,
            "thumbnail": thumbnail,
            "iframe_src": iframe_url,
            "length": duration,
            "template": "videos.html",
        })

    return results
