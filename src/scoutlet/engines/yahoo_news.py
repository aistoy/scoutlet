"""Yahoo News - adapted from SearXNG.

Changes:
- from searx.engines.yahoo.parse_url -> from scoutlet.engines.yahoo.parse_url
- Replaced dateutil.parser with datetime.fromisoformat (where possible)
"""

import logging
import re
from urllib.parse import urlencode
from datetime import datetime, timedelta

from lxml import html

from scoutlet.utils import eval_xpath_list, eval_xpath_getindex, extract_text
from scoutlet.engines.yahoo import parse_url

logger = logging.getLogger("scoutlet.engines.yahoo_news")

about = {
    "website": "https://news.yahoo.com",
    "wikidata_id": "Q3044717",
    "official_api_documentation": "https://developer.yahoo.com/api/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

language_support = False
time_range_support = False
safesearch = False
paging = True
categories = ["news"]

search_url = "https://news.search.yahoo.com/search?{query}&b={offset}"

AGO_RE = re.compile(r"([0-9]+)\s*(year|month|week|day|minute|hour)")
AGO_TIMEDELTA = {
    "minute": timedelta(minutes=1),
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(days=7),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}


def request(query, params):
    offset = (params["pageno"] - 1) * 10 + 1
    params["url"] = search_url.format(offset=offset, query=urlencode({"p": query}))
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for result in eval_xpath_list(dom, '//ol[contains(@class,"searchCenterMiddle")]//li'):
        url = eval_xpath_getindex(result, ".//h4/a/@href", 0, None)
        if url is None:
            continue
        url = parse_url(url)
        title = extract_text(result.xpath(".//h4/a"))
        content = extract_text(result.xpath(".//p"))
        thumbnail = eval_xpath_getindex(result, ".//img/@data-src", 0, None)

        item = {"url": url, "title": title, "content": content, "thumbnail": thumbnail}

        pub_date_text = extract_text(result.xpath('.//span[contains(@class,"s-time")]')) or ""
        ago = AGO_RE.search(pub_date_text)
        if ago:
            try:
                number = int(ago.group(1))
                delta = AGO_TIMEDELTA.get(ago.group(2))
                if delta:
                    item["publishedDate"] = datetime.now() - delta * number
            except (ValueError, TypeError):
                pass
        else:
            try:
                item["publishedDate"] = datetime.fromisoformat(pub_date_text)
            except ValueError:
                pass

        results.append(item)

    for suggestion in eval_xpath_list(dom, '//div[contains(@class,"AlsoTry")]//td'):
        results.append({"suggestion": extract_text(suggestion)})

    return results
