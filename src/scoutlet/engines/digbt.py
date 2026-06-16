"""DigBT (videos/music/files) - adapted from SearXNG."""

import logging
from urllib.parse import urljoin

from lxml import html

from scoutlet.utils import extract_text

logger = logging.getLogger("scoutlet.engines.digbt")

about = {
    "website": "https://digbt.org",
    "wikidata_id": None,
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["videos", "music", "files"]
paging = True

URL = "https://digbt.org"
SEARCH_URL = URL + "/search/{query}-time-{pageno}"
FILESIZE = 3
FILESIZE_MULTIPLIER = 4


def request(query, params):
    params["url"] = SEARCH_URL.format(query=query, pageno=params["pageno"])
    return params


def response(resp):
    dom = html.fromstring(resp.text)
    search_res = dom.xpath('.//td[@class="x-item"]')

    if not search_res:
        return []

    results = []
    for result in search_res:
        try:
            hrefs = result.xpath('.//a[@title]/@href')
            titles = result.xpath('.//a[@title]')
            files_div = result.xpath('.//div[@class="files"]')
            tail_div = result.xpath('.//div[@class="tail"]')
            tail_links = result.xpath('.//div[@class="tail"]//a[@class="title"]/@href')

            if not hrefs or not titles or not tail_links:
                continue

            url = urljoin(URL, hrefs[0])
            title = extract_text(titles[0])
            content = extract_text(files_div[0]) if files_div else ""
            files_data = (extract_text(tail_div[0]) if tail_div else "").split()

            if len(files_data) <= FILESIZE_MULTIPLIER:
                continue

            filesize = f"{files_data[FILESIZE]} {files_data[FILESIZE_MULTIPLIER]}"
            magnetlink = tail_links[0]

            results.append({
                "url": url,
                "title": title,
                "content": content,
                "filesize": filesize,
                "magnetlink": magnetlink,
                "seed": "N/A",
                "leech": "N/A",
                "template": "torrent.html",
            })
        except IndexError:
            continue

    return results
