"""Niconico (videos) - adapted from SearXNG."""

import logging
from urllib.parse import urlencode
from datetime import datetime, timedelta

from lxml import html

from scoutlet.utils import eval_xpath_getindex, eval_xpath_list, eval_xpath, extract_text

logger = logging.getLogger("scoutlet.engines.niconico")

about = {
    "website": "https://www.nicovideo.jp/",
    "wikidata_id": "Q697233",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
    "language": "ja",
}

categories = ["videos"]
paging = True
time_range_support = True
time_range_dict = {"day": 1, "week": 7, "month": 30, "year": 365}

base_url = "https://www.nicovideo.jp"
embed_url = "https://embed.nicovideo.jp"

results_xpath = '//li[@data-video-item]'
url_xpath = './/a[@class="itemThumbWrap"]/@href'
video_length_xpath = './/span[@class="videoLength"]'
upload_time_xpath = './/p[@class="itemTime"]//span[@class="time"]/text()'
title_xpath = './/p[@class="itemTitle"]/a'
content_xpath = './/p[@class="itemDescriptions"]/@title'
thumbnail_xpath = './/img[@class="thumb"]/@src'


def request(query, params):
    query_params = {"page": params["pageno"]}
    if time_range_dict.get(params.get("time_range", "")):
        time_diff_days = time_range_dict[params["time_range"]]
        start_date = datetime.now() - timedelta(days=time_diff_days)
        query_params["start"] = start_date.strftime("%Y-%m-%d")

    params["url"] = f"{base_url}/search/{query}?{urlencode(query_params)}"
    return params


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    for item in eval_xpath_list(dom, results_xpath):
        relative_url = eval_xpath_getindex(item, url_xpath, 0, default="")
        if not relative_url:
            continue
        video_id = relative_url.rsplit("?", maxsplit=1)[0].split("/")[-1]

        url = f"{base_url}/watch/{video_id}"
        iframe_src = f"{embed_url}/watch/{video_id}"

        length = None
        video_length_elem = eval_xpath_getindex(item, video_length_xpath, 0, default=None)
        video_length = extract_text(video_length_elem) if video_length_elem is not None else ""
        if video_length:
            try:
                timediff = datetime.strptime(video_length, "%M:%S")
                length = timedelta(minutes=timediff.minute, seconds=timediff.second)
            except ValueError:
                pass

        published_date = None
        upload_time = eval_xpath_getindex(item, upload_time_xpath, 0, default="")
        if upload_time:
            try:
                published_date = datetime.strptime(upload_time, "%Y/%m/%d %H:%M")
            except ValueError:
                pass

        results.append({
            "template": "videos.html",
            "title": extract_text(eval_xpath(item, title_xpath)) or "",
            "content": eval_xpath_getindex(item, content_xpath, 0, default=""),
            "url": url,
            "iframe_src": iframe_src,
            "thumbnail": eval_xpath_getindex(item, thumbnail_xpath, 0, default=""),
            "length": length,
            "publishedDate": published_date,
        })

    return results
