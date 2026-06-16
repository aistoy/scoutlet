"""Bing search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Uses SearchResult instead of dict
- Removed fetch_traits (loaded from JSON)
"""

import base64
import re
import typing as t
import logging
from urllib.parse import parse_qs, urlencode, urlparse

from lxml import html

from scoutlet.traits import EngineTraits
from scoutlet.result_types import SearchResult
from scoutlet.utils import eval_xpath, eval_xpath_getindex, eval_xpath_list, extract_text

logger = logging.getLogger("scoutlet.engines.bing")

about: dict[str, t.Any] = {
    "website": "https://www.bing.com",
    "wikidata_id": "Q182496",
    "official_api_documentation": "https://github.com/MicrosoftDocs/bing-docs",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["general", "web"]
safesearch = True
_safesearch_map: dict[int, str] = {0: "off", 1: "moderate", 2: "strict"}

base_url = "https://www.bing.com/search"


def get_locale_params(engine_region: str | None) -> dict[str, str] | None:
    if not engine_region or engine_region == "clear":
        return None
    return {"mkt": engine_region}


def override_accept_language(params: dict, engine_region: str | None) -> None:
    if not engine_region or engine_region == "clear":
        return
    lang = engine_region.split("-")[0]
    params["headers"]["Accept-Language"] = f"{engine_region},{lang};q=0.9"


def request(query: str, params: dict[str, t.Any]) -> dict[str, t.Any]:
    engine_region = traits.get_region(params["searxng_locale"], traits.all_locale)

    override_accept_language(params, engine_region)

    query_params: dict[str, str | int] = {
        "q": query,
        "adlt": _safesearch_map.get(params.get("safesearch", 0), "off"),
    }

    locale_params = get_locale_params(engine_region)
    if locale_params:
        query_params.update(locale_params)

    params["url"] = f"{base_url}?{urlencode(query_params)}"
    params["allow_redirects"] = True
    return params


def response(resp) -> list[dict[str, t.Any]]:
    results: list[dict[str, t.Any]] = []
    dom = html.fromstring(resp.text)

    for item in eval_xpath_list(dom, '//ol[@id="b_results"]/li[contains(@class, "b_algo")]'):
        link = eval_xpath_getindex(item, ".//h2/a", 0, None)
        if link is None:
            continue

        href = link.attrib.get("href", "")
        title = extract_text(link)

        if not href or not title:
            continue

        # decode Bing redirect URL
        if href.startswith("https://www.bing.com/ck/a?"):
            qs = parse_qs(urlparse(href).query)
            u_values = qs.get("u")
            if u_values:
                u_val = u_values[0]
                if u_val.startswith("a1"):
                    encoded = u_val[2:]
                    encoded += "=" * (-len(encoded) % 4)
                    href = base64.urlsafe_b64decode(encoded).decode("utf-8", errors="replace")

        # remove decorative icons
        content_els = eval_xpath(item, ".//p")
        for p in content_els:
            for icon in p.xpath('.//span[@class="algoSlug_icon"]'):
                icon.getparent().remove(icon)
        content = extract_text(content_els)

        results.append({"url": href, "title": title, "content": content})

    return results
