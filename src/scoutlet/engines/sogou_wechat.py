"""Sogou WeChat article search engine - adapted from SearXNG.

Changes: from searx → from scoutlet
"""

import re
import logging
from urllib.parse import urlencode
from datetime import datetime
from lxml import html

from scoutlet.utils import extract_text

logger = logging.getLogger("scoutlet.engines.sogou_wechat")

about = {
    "website": "https://weixin.sogou.com/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
    "language": "zh",
}

categories = ["news"]
paging = True

base_url = "https://weixin.sogou.com"


def request(query, params):
    query_params = {
        "query": query,
        "page": params["pageno"],
        "type": 2,
    }

    params["url"] = f"{base_url}/weixin?{urlencode(query_params)}"
    return params


def response(resp):
    dom = html.fromstring(resp.text)
    results = []

    for item in dom.xpath('//li[contains(@id, "sogou_vr_")]'):
        title = extract_text(item.xpath('.//h3/a'))
        url = extract_text(item.xpath('.//h3/a/@href'))

        if url and url.startswith("/link?url="):
            url = f"{base_url}{url}"

        content = extract_text(item.xpath('.//p[@class="txt-info"]'))
        if not content:
            content = extract_text(item.xpath('.//p[contains(@class, "txt-info")]'))

        thumbnail = extract_text(item.xpath('.//div[@class="img-box"]/a/img/@src'))
        if thumbnail and thumbnail.startswith("//"):
            thumbnail = f"https:{thumbnail}"

        published_date = None
        timestamp = extract_text(item.xpath('.//script[contains(text(), "timeConvert")]'))
        if timestamp:
            match = re.search(r"timeConvert\('(\d+)'\)", timestamp)
            if match:
                published_date = datetime.fromtimestamp(int(match.group(1)))

        if title and url:
            results.append({
                "title": title,
                "url": url,
                "content": content,
                "thumbnail": thumbnail,
                "publishedDate": published_date,
            })

    return results
