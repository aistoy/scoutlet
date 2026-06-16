"""Qwant search engine - adapted from SearXNG.

Changes:
- from searx.* → from scoutlet.*
- Removed flask_babel dependency (gettext replaced with plain strings)
- Removed fetch_traits (loaded from JSON)
"""

import logging
from datetime import datetime, timedelta
from json import loads
from urllib.parse import urlencode

import lxml.html

from scoutlet.traits import EngineTraits
from scoutlet.exceptions import (
    SearchEngineAccessDeniedException,
    SearchEngineAPIException,
    SearchEngineCaptchaException,
    SearchEngineTooManyRequestsException,
)
from scoutlet.network import raise_for_httperror
from scoutlet.utils import (
    eval_xpath,
    eval_xpath_list,
    extract_text,
    get_embeded_stream_url,
)

logger = logging.getLogger("scoutlet.engines.qwant")

about = {
    "website": "https://www.qwant.com/",
    "wikidata_id": "Q14657870",
    "official_api_documentation": None,
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["general", "web"]
paging = True
max_page = 5
qwant_categ = None
safesearch = True

qwant_news_locales = [
    'ca_ad', 'ca_es', 'ca_fr', 'co_fr', 'de_at', 'de_ch', 'de_de', 'en_au',
    'en_ca', 'en_gb', 'en_ie', 'en_my', 'en_nz', 'en_us', 'es_ad', 'es_ar',
    'es_cl', 'es_co', 'es_es', 'es_mx', 'es_pe', 'eu_es', 'eu_fr', 'fc_ca',
    'fr_ad', 'fr_be', 'fr_ca', 'fr_ch', 'fr_fr', 'it_ch', 'it_it', 'nl_be',
    'nl_nl', 'pt_ad', 'pt_pt',
]

api_url = "https://api.qwant.com/v3/search/"
web_lite_url = "https://lite.qwant.com/"


def request(query, params):
    if not query:
        return None

    q_locale = traits.get_region(params["searxng_locale"], default="en_US")

    url = api_url + f"{qwant_categ}?"
    args = {"q": query}
    params["raise_for_httperror"] = False

    if qwant_categ == "web-lite":
        url = web_lite_url + "?"
        args["locale"] = q_locale.lower()
        args["l"] = q_locale.split("_")[0]
        args["s"] = params["safesearch"]
        args["p"] = params["pageno"]
        params["raise_for_httperror"] = True

    elif qwant_categ == "images":
        args["count"] = 50
        args["locale"] = q_locale
        args["safesearch"] = params["safesearch"]
        args["tgp"] = 3
        args["offset"] = (params["pageno"] - 1) * args["count"]

    else:  # web, news, videos
        args["count"] = 10
        args["locale"] = q_locale
        args["safesearch"] = params["safesearch"]
        args["llm"] = "false"
        args["tgp"] = 3
        args["offset"] = (params["pageno"] - 1) * args["count"]

    params["url"] = url + urlencode(args)
    return params


def response(resp):
    if qwant_categ == "web-lite":
        return parse_web_lite(resp)
    return parse_web_api(resp)


def parse_web_lite(resp):
    results = []
    dom = lxml.html.fromstring(resp.text)

    for item in eval_xpath_list(dom, "//section/article"):
        if eval_xpath(item, "./span[contains(@class, 'tooltip')]"):
            continue
        results.append({
            "url": extract_text(eval_xpath(item, "./span[contains(@class, 'url partner')]")),
            "title": extract_text(eval_xpath(item, "./h2/a")),
            "content": extract_text(eval_xpath(item, "./p")),
        })

    return results


def parse_web_api(resp):
    results = []

    try:
        search_results = loads(resp.text)
    except ValueError:
        search_results = {}

    data = search_results.get("data", {})

    if search_results.get("status") != "success":
        error_code = data.get("error_code")
        if error_code == 24:
            raise SearchEngineTooManyRequestsException()
        if search_results.get("data", {}).get("error_data", {}).get("captchaUrl") is not None:
            raise SearchEngineCaptchaException()
        if resp.status_code == 403:
            raise SearchEngineAccessDeniedException()
        msg = ",".join(data.get("message", ["unknown"]))
        raise SearchEngineAPIException(f"{msg} ({error_code})")

    raise_for_httperror(resp)

    if qwant_categ == "web":
        mainline = data.get("result", {}).get("items", {}).get("mainline", {})
    else:
        mainline = data.get("result", {}).get("items", [])
        mainline = [{"type": qwant_categ, "items": mainline}]

    if not mainline:
        return []

    for row in mainline:
        mainline_type = row.get("type", "web")
        if mainline_type != qwant_categ:
            continue
        if mainline_type == "ads":
            continue

        for item in row.get("items", []):
            title = item.get("title")
            res_url = item.get("url")

            if mainline_type == "web":
                results.append({
                    "title": title,
                    "url": res_url,
                    "content": item["desc"],
                })

            elif mainline_type == "news":
                pub_date = item["date"]
                if pub_date is not None:
                    pub_date = datetime.fromtimestamp(pub_date)
                news_media = item.get("media", [])
                thumbnail = None
                if news_media:
                    thumbnail = news_media[0].get("pict", {}).get("url")
                results.append({
                    "title": title,
                    "url": res_url,
                    "publishedDate": pub_date,
                    "thumbnail": thumbnail,
                })

            elif mainline_type == "images":
                results.append({
                    "title": title,
                    "url": res_url,
                    "template": "images.html",
                    "thumbnail": item["thumbnail"],
                    "img_src": item["media"],
                })

            elif mainline_type == "videos":
                d, s, c = item.get("desc"), item.get("source"), item.get("channel")
                content_parts = []
                if d:
                    content_parts.append(d)
                if s:
                    content_parts.append(f"Source: {s}")
                if c:
                    content_parts.append(f"Channel: {c}")
                content = " // ".join(content_parts)

                length = item["duration"]
                if length is not None:
                    length = timedelta(milliseconds=length)
                pub_date = item["date"]
                if pub_date is not None:
                    pub_date = datetime.fromtimestamp(pub_date)
                thumbnail = item.get("thumbnail", "")
                if thumbnail:
                    thumbnail = thumbnail.replace("https://s2.qwant.com", "https://s1.qwant.com", 1)

                results.append({
                    "title": title,
                    "url": res_url,
                    "content": content,
                    "iframe_src": get_embeded_stream_url(res_url),
                    "publishedDate": pub_date,
                    "thumbnail": thumbnail,
                    "template": "videos.html",
                })

    return results
