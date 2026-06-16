"""DuckDuckGo Extra (images, videos, news) - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* -> from scoutlet.*
- Removed fetch_traits import
- Replaced searx.network.get with scoutlet.network.get
- Removed type annotations (SXNG_Response, OnlineParams, TYPE_CHECKING)
- Use plain dicts instead of res.types.MainResult
- Use gen_useragent() instead of searxng_useragent()
- Added logger = logging.getLogger("scoutlet.engines.duckduckgo_extra")
- Return list[dict] from response()
- fetch_vqd uses scoutlet.network.get instead of searx.network.get
"""

import logging
import typing as t
from datetime import datetime
from urllib.parse import urlencode, quote_plus

from scoutlet.utils import get_embeded_stream_url, html_to_text, gen_useragent, extr
from scoutlet.network import get as http_get
from scoutlet.engines.duckduckgo import get_ddg_lang, get_vqd, set_vqd, _HTTP_User_Agent

logger = logging.getLogger("scoutlet.engines.duckduckgo_extra")

about = {
    "website": "https://duckduckgo.com/",
    "wikidata_id": "Q12805",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON (site requires js to get images)",
}

# engine dependent config
# duckduckgo_extra collapses SearXNG's duckduckgo_images/videos/news into one
# module (selected via ddg_category); list all three so it shows up under each.
categories = ["images", "videos", "news"]
ddg_category = ""
"""The category must be any of ``images``, ``videos`` and ``news``"""
paging = True
safesearch = True

safesearch_cookies = {0: "-2", 1: None, 2: "1"}
safesearch_args = {0: "1", 1: None, 2: "1"}
search_path_map = {"images": "i", "videos": "v", "news": "news"}


def init(engine_settings: dict[str, t.Any]):
    if engine_settings["ddg_category"] not in ["images", "videos", "news"]:
        raise ValueError(f"Unsupported DuckDuckGo category: {engine_settings['ddg_category']}")


def fetch_vqd(query: str, params: dict):
    """Fetch vqd value from duckduckgo.com when not in cache."""
    logger.debug("fetch_vqd: request value from from duckduckgo.com")
    resp = http_get(
        url=f"https://duckduckgo.com/?q={quote_plus(query)}&iar=images&t=h_",
        headers=params["headers"],
        timeout=2,
    )
    value = ""
    if resp.status_code == 200:
        value = extr(resp.text, 'vqd="', '"')
        if value:
            logger.debug("vqd value from duckduckgo.com request: '%s'", value)
        else:
            logger.error("vqd: can't parse value from ddg response (return empty string)")
            return ""
    else:
        logger.error("vqd: got HTTP %s from duckduckgo.com", resp.status_code)

    if value:
        set_vqd(query=query, value=value, ua=_HTTP_User_Agent)
    else:
        logger.error("none vqd value from duckduckgo.com: HTTP %s", resp.status_code)
    return value


def request(query: str, params: dict) -> None:
    if len(query) >= 500:
        # DDG does not accept queries with more than 499 chars
        params["url"] = None
        return

    # HTTP headers
    # ============
    headers = params["headers"]

    # The vqd value is generated from the query and the UA header. To be able to
    # reuse the vqd value, the UA header must be static.
    headers["User-Agent"] = _HTTP_User_Agent

    vqd = get_vqd(query=query, ua=_HTTP_User_Agent) or fetch_vqd(query=query, params=params)

    headers["Accept"] = "*/*"
    headers["Referer"] = "https://duckduckgo.com/"
    headers["Host"] = "duckduckgo.com"

    # DDG XHTMLRequest
    # ================
    eng_region: str = traits.get_region(
        params["searxng_locale"],
        traits.all_locale,
    )
    eng_lang: str = get_ddg_lang(traits, params["searxng_locale"]) or "wt-wt"

    args: dict[str, str | int] = {
        "o": "json",
        "q": query,
        "u": "bing",
        "l": eng_region,
        "bpia": "1",
        "vqd": vqd,
        "a": "h_",
    }

    params["cookies"]["ad"] = eng_lang  # zh_CN
    params["cookies"]["ah"] = eng_region  # "us-en,de-de"
    params["cookies"]["l"] = eng_region  # "hk-tzh"

    args["ct"] = "EN"
    if params["searxng_locale"] != "all":
        args["ct"] = params["searxng_locale"].split("-")[0].upper()

    if params["pageno"] > 1:
        args["s"] = (params["pageno"] - 1) * 100

    safe_search = safesearch_cookies.get(params["safesearch"])
    if safe_search is not None:
        params["cookies"]["p"] = safe_search  # "-2", "1"
        args["p"] = safe_search

    params["url"] = f"https://duckduckgo.com/{search_path_map[ddg_category]}.js?{urlencode(args)}"
    logger.debug("param headers: %s", params["headers"])
    logger.debug("param data: %s", params["data"])
    logger.debug("param cookies: %s", params["cookies"])


def _image_result(result):
    return {
        'template': 'images.html',
        'url': result['url'],
        'title': result['title'],
        'content': '',
        'thumbnail_src': result['thumbnail'],
        'img_src': result['image'],
        'resolution': '%s x %s' % (result['width'], result['height']),
        'source': result['source'],
    }


def _video_result(result):
    return {
        'template': 'videos.html',
        'url': result['content'],
        'title': result['title'],
        'content': result['description'],
        'thumbnail': result['images'].get('small') or result['images'].get('medium'),
        'iframe_src': get_embeded_stream_url(result['content']),
        'source': result['provider'],
        'length': result['duration'],
        'metadata': result.get('uploader'),
    }


def _news_result(result):
    return {
        'url': result['url'],
        'title': result['title'],
        'content': html_to_text(result['excerpt']),
        'source': result['source'],
        'publishedDate': datetime.fromtimestamp(result['date']),
    }


def response(resp):
    results = []
    res_json = resp.json()

    for result in res_json['results']:
        if ddg_category == 'images':
            results.append(_image_result(result))
        elif ddg_category == 'videos':
            results.append(_video_result(result))
        elif ddg_category == 'news':
            results.append(_news_result(result))
        else:
            raise ValueError(f"Invalid duckduckgo category: {ddg_category}")

    return results
