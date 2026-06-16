"""DuckDuckGo search engine (HTML/lite) - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Removed fetch_traits (traits loaded from JSON)
- Removed EngineCache/vqd caching (uses simple dict keyed by query+UA)
- Removed external bangs support
- Removed SXNG_Response/OnlineParams type annotations
- Simplified to use dict-based results (compatible with EngineResults)
- Removed ddg_reg_map/ddg_lang_map (only used by fetch_traits)
"""

import logging
import typing as t

from lxml import html

from scoutlet.exceptions import SearchEngineCaptchaException
from scoutlet.result_types import EngineResults
from scoutlet.utils import (
    eval_xpath,
    eval_xpath_getindex,
    extract_text,
    gen_useragent,
)

logger = logging.getLogger("scoutlet.engines.duckduckgo")

about = {
    "website": "https://lite.duckduckgo.com/lite/",
    "wikidata_id": "Q12805",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["general"]
paging = True
time_range_support = True
safesearch = True

ddg_url = "https://html.duckduckgo.com/html/"

time_range_dict = {"day": "d", "week": "w", "month": "m", "year": "y"}

# In-memory vqd cache keyed by (query, user_agent)
_vqd_cache: dict[str, str] = {}

# Static User-Agent: DDG's bot blocker ties vqd to the UA, so it must not change
_HTTP_User_Agent: str = gen_useragent()


def set_vqd(query: str, value: str, ua: str) -> None:
    _vqd_cache[f"{query}//{ua}"] = value


def get_vqd(query: str, ua: str) -> str:
    return _vqd_cache.get(f"{query}//{ua}", "")


def get_ddg_lang(traits_obj, locale: str) -> str:
    if locale == "all":
        return "wt-wt"
    lang = traits_obj.get_language(locale)
    return lang or "wt-wt"


def request(query: str, params: dict[str, t.Any]) -> None:
    if len(query) >= 500:
        params["url"] = None
        return

    # zh locales: DDG does not have a "next page" button and returns 403
    locale = params.get("searxng_locale", "all")
    if locale.startswith("zh") and params["pageno"] > 1:
        params["url"] = None
        return

    eng_region = traits.get_region(
        locale,
        traits.all_locale,
    )

    # HTTP headers
    headers = params["headers"]

    # Static UA: vqd is tied to the User-Agent, must not change between pages
    headers["User-Agent"] = _HTTP_User_Agent

    # Remove Accept header: DDG's bot blocker checks for Python-style Accept values.
    # A real browser navigating via form POST does not always send Accept.
    headers.pop("Accept", None)

    headers["Sec-Fetch-Dest"] = "document"
    headers["Sec-Fetch-Mode"] = "navigate"
    headers["Sec-Fetch-Site"] = "same-origin"
    headers["Sec-Fetch-User"] = "?1"

    ui_lang = locale if locale != "all" else "en"
    headers["Accept-Language"] = f"{ui_lang},{ui_lang}-{ui_lang.upper()};q=0.7"

    # DDG uses POST with form data; disable redirect following (SearXNG does the same)
    params["allow_redirects"] = False
    params["method"] = "POST"
    params["url"] = ddg_url

    # DDG search form (POST data)
    data = params.get("data", {})
    if isinstance(data, dict):
        data = dict(data)  # copy to avoid mutating shared default
    data["q"] = query

    if params["pageno"] == 1:
        data["b"] = ""
    else:
        vqd = get_vqd(query=query, ua=_HTTP_User_Agent)
        if vqd:
            data["vqd"] = vqd
        else:
            raise SearchEngineCaptchaException(
                suspended_time=0,
                message=f"VQD missed (page: {params['pageno']})",
            )

        data["nextParams"] = ""
        data["api"] = "d.js"
        data["o"] = "json"
        data["v"] = "l"

        offset = 10 + (params["pageno"] - 2) * 15
        data["dc"] = offset + 1
        data["s"] = offset

    if eng_region == "wt-wt":
        data["kl"] = "wt-wt"
    else:
        data["kl"] = eng_region
        params["cookies"]["kl"] = eng_region

    t_range = time_range_dict.get(str(params.get("time_range", "")), "")
    if t_range:
        data["df"] = t_range
        params["cookies"]["df"] = t_range

    params["data"] = data
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    headers["Referer"] = ddg_url


def is_ddg_captcha(dom):
    return bool(eval_xpath(dom, "//form[@id='challenge-form']"))


def response(resp) -> EngineResults:
    res = EngineResults()

    if resp.status_code == 303:
        return res

    doc = html.fromstring(resp.text)
    search_params = getattr(resp, 'search_params', {})

    if is_ddg_captcha(doc):
        raise SearchEngineCaptchaException(
            suspended_time=0,
            message="CAPTCHA detected",
        )

    # Extract vqd from form for subsequent pages
    form = eval_xpath(doc, '//input[@name="vqd"]/..')
    if len(form):
        form = form[0]
        form_vqd = eval_xpath(form, '//input[@name="vqd"]/@value')
        if form_vqd:
            q = str(search_params.get("data", {}).get("q", ""))
            if q:
                set_vqd(query=q, value=str(form_vqd[0]), ua=_HTTP_User_Agent)

    # Parse web results
    for div_result in eval_xpath(doc, '//div[@id="links"]/div[contains(@class, "web-result")]'):
        _title = eval_xpath(div_result, ".//h2/a")
        _content = eval_xpath_getindex(div_result, './/a[contains(@class, "result__snippet")]', 0, [])
        _url = eval_xpath(div_result, ".//h2/a/@href")

        if _url:
            res.append({
                "title": extract_text(_title) or "",
                "url": _url[0],
                "content": extract_text(_content) or "",
            })

    # Parse zero-click info
    zero_click_info_xpath = '//div[@id="zero_click_abstract"]'
    zero_click = extract_text(eval_xpath(doc, zero_click_info_xpath)).strip()

    if zero_click and (
        "Your IP address is" not in zero_click
        and "Your user agent:" not in zero_click
        and "URL Decoded:" not in zero_click
    ):
        _zc_url = eval_xpath_getindex(doc, '//div[@id="zero_click_abstract"]/a/@href', 0)
        res.append({
            "url": _zc_url or "",
            "title": "",
            "content": zero_click,
        })

    return res
