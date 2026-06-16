"""Bandcamp music search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Replaced dateutil.parser with datetime.strptime for "Month Day, Year" format
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
"""

import logging
from datetime import datetime
from urllib.parse import quote, urljoin

from lxml import html

from scoutlet.utils import eval_xpath, eval_xpath_list, extract_text

logger = logging.getLogger("scoutlet.engines.bandcamp")

about = {
    "website": "https://bandcamp.com/",
    "wikidata_id": "Q12843860",
    "official_api_documentation": "",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["music"]
paging = True

search_url = "https://bandcamp.com/search?q={query}&page={pageno}"


def request(query, params):
    params["url"] = search_url.format(
        query=quote(query),
        pageno=params["pageno"],
    )
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for result in eval_xpath_list(dom, '//li[@class="searchresult data"]', min_len=0):
        item_type = extract_text(eval_xpath(result, './/div[@class="itemtype"]'))
        item_type = (item_type or "").strip().lower()

        title_elem = eval_xpath(result, './/div[@class="heading"]//text()')
        title = extract_text(title_elem) if title_elem else ""

        url_elem = eval_xpath(result, './/div[@class="heading"]/a/@href')
        url = url_elem[0].strip() if url_elem else ""

        content_elem = eval_xpath(result, './/div[@class="subhead"]')
        content = extract_text(content_elem) if content_elem else ""

        # Try to extract release date from the subhead or released field
        publishedDate = None
        released_elem = eval_xpath(result, './/div[@class="released"]')
        if released_elem:
            date_str = extract_text(released_elem)
            if date_str:
                # Remove "released " prefix and parse
                date_str = date_str.replace("released", "").strip()
                try:
                    publishedDate = datetime.strptime(date_str, "%B %d, %Y")
                except ValueError:
                    try:
                        publishedDate = datetime.strptime(date_str, "%d %B %Y")
                    except ValueError:
                        pass

        thumbnail_elem = eval_xpath(result, './/div[@class="art"]//img/@src')
        thumbnail = thumbnail_elem[0] if thumbnail_elem else ""

        result_item = {
            "url": url,
            "title": title,
            "content": content,
            "publishedDate": publishedDate,
            "thumbnail": thumbnail,
        }

        if "album" in item_type:
            result_item["template"] = "videos.html"
        elif "track" in item_type:
            result_item["template"] = "videos.html"
        elif "artist" in item_type:
            pass  # default result

        results.append(result_item)

    return results
