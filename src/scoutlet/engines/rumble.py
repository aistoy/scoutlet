"""Rumble (videos) - adapted from SearXNG."""

import logging
from datetime import datetime
from urllib.parse import urlencode

from lxml import html

from scoutlet.utils import extract_text

logger = logging.getLogger("scoutlet.engines.rumble")

about = {
    "website": "https://rumble.com/",
    "wikidata_id": "Q104765127",
    "official_api_documentation": "https://help.rumble.com/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["videos"]
paging = True

base_url = "https://rumble.com/"

url_xpath = './/a[@class="video-item--a"]/@href'
thumbnail_xpath = './/img[@class="video-item--img"]/@src'
title_xpath = './/h3[@class="video-item--title"]'
published_date_xpath = './/time[@class="video-item--meta video-item--time"]/@datetime'
earned_xpath = './/span[@class="video-item--meta video-item--earned"]/@data-value'
views_xpath = './/span[@class="video-item--meta video-item--views"]/@data-value'
rumbles_xpath = './/span[@class="video-item--meta video-item--rumbles"]/@data-value'
author_xpath = './/div[@class="ellipsis-1"]'
length_xpath = './/span[@class="video-item--duration"]/@data-value'


def request(query, params):
    args = {"q": query}
    if params["pageno"] > 1:
        args["page"] = params["pageno"]
    params["url"] = f"{base_url}search/video?{urlencode(args)}"
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)
    results_dom = dom.xpath('//li[contains(@class, "video-listing-entry")]')

    if not results_dom:
        return []

    for result_dom in results_dom:
        href = extract_text(result_dom.xpath(url_xpath)) or ""
        url = base_url + href.lstrip("/") if href else ""
        thumbnail = extract_text(result_dom.xpath(thumbnail_xpath)) or ""
        title = extract_text(result_dom.xpath(title_xpath)) or ""
        p_date = extract_text(result_dom.xpath(published_date_xpath)) or ""
        if not p_date:
            continue
        try:
            fixed_date = datetime.strptime(p_date, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            fixed_date = None
        earned = extract_text(result_dom.xpath(earned_xpath))
        views = extract_text(result_dom.xpath(views_xpath))
        rumbles = extract_text(result_dom.xpath(rumbles_xpath))
        author = extract_text(result_dom.xpath(author_xpath))
        length = extract_text(result_dom.xpath(length_xpath))

        if earned:
            content = f"{views} views - {rumbles} rumbles - ${earned}"
        else:
            content = f"{views} views - {rumbles} rumbles"

        results.append({
            "url": url,
            "title": title,
            "content": content,
            "author": author,
            "length": length,
            "template": "videos.html",
            "publishedDate": fixed_date,
            "thumbnail": thumbnail,
        })
    return results
