"""Google search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Removed fetch_traits (loaded from JSON)
- Simplified get_google_info (no babel locale parsing, uses searxng_locale directly)
- Removed ui_async (not needed for basic usage)
- Removed type annotations for SXNG_Response/OnlineParams
"""

import re
import logging
import typing as t
from urllib.parse import unquote, urlencode

from lxml import html

from scoutlet.exceptions import SearchEngineCaptchaException
from scoutlet.result_types import SearchResult, EngineResults
from scoutlet.utils import (
    eval_xpath,
    eval_xpath_getindex,
    eval_xpath_list,
    extract_text,
    gen_gsa_useragent,
)

logger = logging.getLogger("scoutlet.engines.google")

about = {
    "website": "https://www.google.com",
    "wikidata_id": "Q9366",
    "official_api_documentation": "https://developers.google.com/custom-search/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

# engine dependent config
categories = ["general"]
paging = True
max_page = 50
time_range_support = True
safesearch = True

time_range_dict = {"day": "d", "week": "w", "month": "m", "year": "y"}

# Filter results. 0: None, 1: Moderate, 2: Strict
filter_mapping = {0: "off", 1: "medium", 2: "high"}

# specific xpath variables
suggestion_xpath = '//div[contains(@class, "gGQDvd iIWm4b")]//a'


def get_google_info(params: dict[str, t.Any], eng_traits) -> dict[str, t.Any]:
    """Composing various (language) properties for the Google engines.

    Simplified from SearXNG: no babel locale parsing, uses searxng_locale directly
    to look up language/region from engine traits.
    """
    ret_val: dict[str, t.Any] = {
        "language": None,
        "country": None,
        "subdomain": "www.google.com",
        "params": {},
        "headers": {},
        "cookies": {},
    }

    sxng_locale = params.get("searxng_locale", "all")

    eng_lang = eng_traits.get_language(sxng_locale, "lang_en")
    lang_code = eng_lang.split("_")[-1]  # lang_zh-TW --> zh-TW / lang_en --> en
    country = eng_traits.get_region(sxng_locale, eng_traits.all_locale)

    ret_val["language"] = eng_lang
    ret_val["country"] = country

    if hasattr(eng_traits, 'custom') and "supported_domains" in eng_traits.custom:
        ret_val["subdomain"] = eng_traits.custom["supported_domains"].get(
            (country or "").upper(), "www.google.com"
        )

    ret_val["params"]["hl"] = f"{lang_code}-{country}" if country else lang_code
    ret_val["params"]["lr"] = eng_lang if sxng_locale != "all" else ""
    ret_val["params"]["cr"] = ""
    if sxng_locale != "all" and "-" in sxng_locale:
        ret_val["params"]["cr"] = "country" + (country or "")
    ret_val["params"]["ie"] = "utf8"
    ret_val["params"]["oe"] = "utf8"

    ret_val["headers"]["Accept"] = "*/*"
    ret_val["headers"]["User-Agent"] = gen_gsa_useragent()
    ret_val["cookies"]["CONSENT"] = "YES+"

    return ret_val


def detect_google_sorry(resp):
    if hasattr(resp, 'url') and resp.url:
        url_str = str(resp.url)
        if "sorry.google.com" in url_str or "/sorry" in url_str.split("?")[0].split("//")[-1]:
            raise SearchEngineCaptchaException()
    text = resp.text if hasattr(resp, 'text') else ""
    if "sorry.google.com" in text or "/sorry/index" in text:
        raise SearchEngineCaptchaException()


def request(query: str, params: dict[str, t.Any]) -> None:
    """Google search request"""
    start = (params["pageno"] - 1) * 10
    google_info = get_google_info(params, traits)

    query_url = (
        "https://"
        + google_info["subdomain"]
        + "/search"
        + "?"
        + urlencode(
            {
                "q": query,
                **google_info["params"],
                "filter": "0",
                "start": start,
            }
        )
    )

    if params.get("time_range") in time_range_dict:
        query_url += "&" + urlencode({"tbs": "qdr:" + time_range_dict[params["time_range"]]})
    if params.get("safesearch"):
        query_url += "&" + urlencode({"safe": filter_mapping.get(params["safesearch"], "off")})
    params["url"] = query_url

    params["cookies"] = google_info["cookies"]
    params["headers"].update(google_info["headers"])


# regex match to get image map from javascript
RE_DATA_IMAGE = re.compile(r"(data:image[^']*?)'[^']*?'((?:dimg|pimg|tsuid)[^']*)")


def parse_url_images(text: str):
    data_image_map = {}
    for image_url, img_id in RE_DATA_IMAGE.findall(text):
        data_image_map[img_id] = image_url.encode('utf-8').decode("unicode-escape")
    return data_image_map


def response(resp) -> EngineResults:
    """Get response from google's search request"""
    detect_google_sorry(resp)
    data_image_map = parse_url_images(resp.text)

    results = EngineResults()
    dom = html.fromstring(resp.text)

    # parse results
    for result in eval_xpath_list(dom, '//a[@data-ved and not(@class)]'):
        try:
            title_tag = eval_xpath_getindex(result, './/div[@style]', 0, default=None)
            if title_tag is None:
                continue
            title = extract_text(title_tag)

            raw_url = result.get("href")
            if raw_url is None:
                continue

            if raw_url.startswith('/url?q='):
                url = unquote(raw_url[7:].split("&sa=U")[0])
            else:
                url = raw_url

            content_nodes = eval_xpath(result, '../..//div[contains(@class, "ilUpNd H66NU aSRlid")]')
            for item in content_nodes:
                for script in item.xpath(".//script"):
                    script.getparent().remove(script)

            content = extract_text(content_nodes[0]) if content_nodes else ""

            xpath_image = eval_xpath_getindex(result, './/img', index=0, default=None)

            thumbnail = None
            if xpath_image is not None:
                thumbnail = xpath_image.get("src")
                if thumbnail and thumbnail.startswith("data:image"):
                    img_id = xpath_image.get("id")
                    if img_id:
                        thumbnail = data_image_map.get(img_id)

            results.append({
                "url": url,
                "title": title,
                "content": content or '',
                "thumbnail": thumbnail,
            })

        except Exception as e:
            logger.error(e, exc_info=True)
            continue

    # parse suggestion
    for suggestion in eval_xpath_list(dom, suggestion_xpath):
        results.append({"suggestion": extract_text(suggestion)})

    return results
