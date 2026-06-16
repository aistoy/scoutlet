"""Brave search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Uses SearchResult instead of LegacyResult
- Removed fetch_traits (traits loaded from JSON)
- Simplified logger
"""

import json
import typing as t
import logging
from urllib.parse import urlencode, urlparse

from lxml import html

from scoutlet import locales
from scoutlet.traits import EngineTraits
from scoutlet.result_types import SearchResult, EngineResults
from scoutlet.utils import (
    eval_xpath_getindex,
    eval_xpath_list,
    extract_text,
    get_embeded_stream_url,
    js_obj_str_to_json_str,
)

logger = logging.getLogger("scoutlet.engines.brave")

about = {
    "website": "https://search.brave.com/",
    "wikidata_id": "Q22906900",
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

base_url = "https://search.brave.com/"
categories = []
brave_category: t.Literal["search", "videos", "images", "news", "goggles"] = "search"
Goggles: str = ""
brave_spellcheck = False
paging = False
max_page = 10
safesearch = True
safesearch_map = {2: "strict", 1: "moderate", 0: "off"}
time_range_support = False
time_range_map: dict[str, str] = {"day": "pd", "week": "pw", "month": "pm", "year": "py"}


def request(query: str, params: dict[str, t.Any]) -> None:
    args: dict[str, t.Any] = {"q": query, "source": "web"}
    if brave_spellcheck:
        args["spellcheck"] = "1"

    if brave_category in ("search", "goggles"):
        if params.get("pageno", 1) - 1:
            args["offset"] = params.get("pageno", 1) - 1
        if time_range_map.get(params["time_range"]):
            args["tf"] = time_range_map.get(params["time_range"])

    if brave_category == "goggles":
        args["goggles_id"] = Goggles

    params["headers"]["Accept-Encoding"] = "gzip, deflate"
    params["url"] = f"{base_url}{brave_category}?{urlencode(args)}"

    params["cookies"]["safesearch"] = safesearch_map.get(params["safesearch"], "off")
    params["cookies"]["useLocation"] = "0"
    params["cookies"]["summarizer"] = "0"

    engine_region = traits.get_region(params["searxng_locale"], "all")
    if engine_region and engine_region != "all":
        params["cookies"]["country"] = engine_region.split("-")[-1].lower()

    if hasattr(traits, 'custom') and "ui_lang" in traits.custom:
        ui_lang = locales.get_engine_locale(params["searxng_locale"], traits.custom["ui_lang"], "en-us")
        params["cookies"]["ui_lang"] = ui_lang


def _extract_published_date(published_date_raw: str | None):
    if published_date_raw is None:
        return None
    try:
        from dateutil import parser
        return parser.parse(published_date_raw)
    except Exception:
        return None


def extract_json_data(text: str) -> dict[str, t.Any]:
    text = text[text.index("<script") : text.index("</script>")]
    if not text:
        raise ValueError("can't find JS/JSON data in the given text")
    start = text.index("data: [{")
    end = text.rindex("}}]")
    js_obj_str = text[start:end]
    js_obj_str = "{" + js_obj_str + "}}]}"
    json_str = js_obj_str_to_json_str(js_obj_str)
    data: dict[str, t.Any] = json.loads(json_str)
    return data


def response(resp) -> EngineResults:
    if brave_category in ("search", "goggles"):
        return _parse_search(resp)
    if brave_category in ("news",):
        return _parse_news(resp)

    json_data: dict[str, t.Any] = extract_json_data(resp.text)
    json_resp: dict[str, t.Any] = json_data["data"][1]["data"]["body"]["response"]

    if brave_category == "images":
        return _parse_images(json_resp)
    if brave_category == "videos":
        return _parse_videos(json_resp)

    raise ValueError(f"Unsupported brave category: {brave_category}")


def _parse_search(resp) -> EngineResults:
    res = EngineResults()
    dom = html.fromstring(resp.text)

    for result in eval_xpath_list(dom, "//div[contains(@class, 'snippet ')]"):
        url: str | None = eval_xpath_getindex(result, ".//a/@href", 0, default=None)
        title_tag = eval_xpath_getindex(result, ".//div[contains(@class, 'title')]", 0, default=None)
        if url is None or title_tag is None or not urlparse(url).netloc:
            continue

        content: str = ""
        pub_date = None

        _content = eval_xpath_getindex(
            result,
            ".//div[contains(concat(' ', @class, ' '), ' content ')]",
            0,
            default="",
        )
        if len(_content):
            content = extract_text(_content)
            _pub_date = extract_text(
                eval_xpath_getindex(_content, ".//span[contains(@class, 't-secondary')]", 0, default="")
            )
            if _pub_date:
                pub_date = _extract_published_date(_pub_date)
                content = content.lstrip(_pub_date).strip("- \n\t")

        thumbnail: str = eval_xpath_getindex(result, ".//a[contains(@class, 'thumbnail')]//img/@src", 0, default="")

        item = SearchResult(
            template="default.html",
            url=url,
            title=extract_text(title_tag),
            content=content or "",
            publishedDate=pub_date,
            thumbnail=thumbnail or "",
        )
        res.add(item)

        video_tag = eval_xpath_getindex(
            result,
            ".//div[contains(@class, 'video-snippet') and @data-macro='video']",
            0,
            default=[],
        )
        if len(video_tag):
            iframe_src = get_embeded_stream_url(url)
            if iframe_src:
                item.iframe_src = iframe_src
                item.template = "videos.html"

    return res


def _parse_news(resp) -> EngineResults:
    res = EngineResults()
    dom = html.fromstring(resp.text)

    for result in eval_xpath_list(dom, "//div[contains(@class, 'results')]//div[@data-type='news']"):
        url = eval_xpath_getindex(result, ".//a[contains(@class, 'result-header')]/@href", 0, default=None)
        if url is None:
            continue

        title = eval_xpath_list(result, ".//span[contains(@class, 'snippet-title')]")
        content = eval_xpath_list(result, ".//p[contains(@class, 'desc')]")
        thumbnail = eval_xpath_getindex(result, ".//div[contains(@class, 'image-wrapper')]//img/@src", 0, default="")

        item = SearchResult(
            template="default.html",
            url=url,
            title=extract_text(title),
            thumbnail=thumbnail or "",
            content=extract_text(content) or "",
        )
        res.add(item)

    return res


def _parse_images(json_resp: dict[str, t.Any]) -> EngineResults:
    res = EngineResults()
    for result in json_resp["results"]:
        item = SearchResult(
            template="images.html",
            url=result["url"],
            title=result["title"],
            img_src=result["properties"]["url"],
            thumbnail=result["thumbnail"]["src"],
        )
        res.add(item)
    return res


def _parse_videos(json_resp: dict[str, t.Any]) -> EngineResults:
    res = EngineResults()
    for result in json_resp["results"]:
        item = SearchResult(
            template="videos.html",
            url=result["url"],
            title=result["title"],
            content=result.get("description", ""),
        )
        if result.get("age"):
            item.publishedDate = _extract_published_date(result["age"])
        if result.get("thumbnail"):
            item.thumbnail = result["thumbnail"]["src"]
        iframe_src = get_embeded_stream_url(result["url"])
        if iframe_src:
            item.iframe_src = iframe_src
        res.add(item)
    return res
