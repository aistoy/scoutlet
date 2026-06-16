"""Bing News search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* -> from scoutlet.*
- Removed fetch_traits function (was just delegating to bing.fetch_traits)
- Removed type annotations (SXNG_Response, OnlineParams, TYPE_CHECKING)
- Use plain dicts instead of res.types.MainResult
- Use gen_useragent() instead of searxng_useragent()
- Added logger = logging.getLogger("scoutlet.engines.bing_news")
- Return list[dict] from response()
"""

import logging
from urllib.parse import urlencode

from lxml import html

from scoutlet.engines.bing import (
    get_locale_params,
    override_accept_language,
)
from scoutlet.utils import eval_xpath, eval_xpath_getindex, eval_xpath_list, extract_text

logger = logging.getLogger("scoutlet.engines.bing_news")

about = {
    "website": "https://www.bing.com/news",
    "wikidata_id": "Q2878637",
    "official_api_documentation": "https://github.com/MicrosoftDocs/bing-docs",
    "use_official_api": False,
    "require_api_key": False,
    "results": "RSS",
}

# engine dependent config
categories = ["news"]
paging = True
"""If go through the pages and there are actually no new results for another
page, then bing returns the results from the last page again."""
time_range_support = True

time_map = {
    "day": 'interval="4"',
    "week": 'interval="7"',
    "month": 'interval="9"',
}
"""A string '4' means *last hour*. We use *last hour* for ``day`` here since the
difference of *last day* and *last week* in the result list is just marginally.
Bing does not have news range ``year`` / we use ``month`` instead."""

base_url = "https://www.bing.com/news/infinitescrollajax"
"""Bing (News) search URL"""


def request(query, params):
    """Assemble a Bing-News request."""
    engine_region = traits.get_region(params["searxng_locale"], traits.all_locale)
    override_accept_language(params, engine_region)

    # build URL query
    # - example: https://www.bing.com/news/infinitescrollajax?q=london&first=1
    page = int(params.get("pageno", 1)) - 1
    query_params = {
        "q": query,
        "InfiniteScroll": 1,
        # to simplify the page count lets use the default of 10 images per page
        "first": page * 10 + 1,
        "SFX": page,
        "form": "PTFTNR",
    }

    locale_params = get_locale_params(engine_region)
    if locale_params:
        query_params.update(locale_params)

    if params["time_range"]:
        query_params["qft"] = time_map.get(params["time_range"], 'interval="9"')

    params["url"] = base_url + "?" + urlencode(query_params)
    return params


def response(resp):
    """Parse the Bing-News response."""
    results = []
    dom = html.fromstring(resp.text)

    for newsitem in eval_xpath_list(dom, '//div[contains(@class, "newsitem")]'):
        link = eval_xpath_getindex(newsitem, './/a[@class="title"]', 0, None)
        if link is None:
            continue
        url = link.attrib.get("href")
        title = extract_text(link)
        content = extract_text(eval_xpath(newsitem, './/div[@class="snippet"]'))

        metadata = []
        source = eval_xpath_getindex(newsitem, './/div[contains(@class, "source")]', 0, None)
        if source is not None:
            for item in (
                eval_xpath_getindex(source, ".//span[@aria-label]/@aria-label", 0, None),
                link.attrib.get("data-author"),
            ):
                if item is not None:
                    t = extract_text(item)
                    if t and t.strip():
                        metadata.append(t.strip())
        metadata = " | ".join(metadata)

        thumbnail = None
        imagelink = eval_xpath_getindex(newsitem, './/a[@class="imagelink"]//img', 0, None)
        if imagelink is not None:
            thumbnail = imagelink.attrib.get("src")
            if not thumbnail.startswith("https://www.bing.com"):
                thumbnail = "https://www.bing.com/" + thumbnail

        results.append(
            {
                "url": url,
                "title": title,
                "content": content,
                "thumbnail": thumbnail,
                "metadata": metadata,
            }
        )

    return results
