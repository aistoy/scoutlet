"""Flickr (Images) - no API key, HTML scraping. Adapted from SearXNG."""

import json
import logging
import re
from time import time
from urllib.parse import urlencode

from scoutlet.utils import ecma_unescape, html_to_text

logger = logging.getLogger("scoutlet.engines.flickr_noapi")

about = {
    "website": "https://www.flickr.com",
    "wikidata_id": "Q103204",
    "official_api_documentation": "https://secure.flickr.com/services/api/flickr.photos.search.html",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["images"]
paging = True
time_range_support = True
safesearch = False

time_range_dict = {
    "day": 60 * 60 * 24,
    "week": 60 * 60 * 24 * 7,
    "month": 60 * 60 * 24 * 7 * 4,
    "year": 60 * 60 * 24 * 7 * 52,
}
image_sizes = ("o", "k", "h", "b", "c", "z", "m", "n", "t", "q", "s")

search_url = "https://www.flickr.com/search?{query}&page={page}"
time_range_url = "&min_upload_date={start}&max_upload_date={end}"
photo_url = "https://www.flickr.com/photos/{userid}/{photoid}"
modelexport_re = re.compile(r"^\s*modelExport:\s*({.*}),$", re.M)


def build_flickr_url(user_id, photo_id):
    return photo_url.format(userid=user_id, photoid=photo_id)


def _get_time_range_url(time_range):
    if time_range in time_range_dict:
        return time_range_url.format(
            start=time(), end=str(int(time()) - time_range_dict[time_range])
        )
    return ""


def request(query, params):
    params["url"] = search_url.format(
        query=urlencode({"text": query}), page=params["pageno"]
    ) + _get_time_range_url(params.get("time_range", ""))
    return params


def response(resp):
    results = []

    matches = modelexport_re.search(resp.text)
    if matches is None:
        return results

    match = matches.group(1)
    model_export = json.loads(match)

    if "legend" not in model_export:
        return results
    legend = model_export["legend"]

    if not legend or not legend[0]:
        return results

    for x, index in enumerate(legend):
        if len(index) != 8:
            continue

        try:
            photo = (
                model_export["main"][index[0]][int(index[1])][index[2]][index[3]]
                [index[4]][index[5]][int(index[6])][index[7]]
            )
        except (IndexError, KeyError, TypeError, ValueError):
            continue

        author = ecma_unescape(photo.get("realname", ""))
        source = ecma_unescape(photo.get("username", ""))
        if source:
            source += " @ Flickr"
        title = ecma_unescape(photo.get("title", ""))
        content = html_to_text(ecma_unescape(photo.get("description", "")))

        size_data = None
        for image_size in image_sizes:
            try:
                if image_size in photo["sizes"]["data"]:
                    size_data = photo["sizes"]["data"][image_size]["data"]
                    break
            except (KeyError, TypeError):
                continue

        if not size_data:
            continue

        img_src = size_data.get("url", "")
        resolution = "%s x %s" % (size_data.get("width", "?"), size_data.get("height", "?"))

        try:
            thumb_data = photo["sizes"]["data"]
            if "n" in thumb_data:
                thumbnail_src = thumb_data["n"]["data"]["url"]
            elif "z" in thumb_data:
                thumbnail_src = thumb_data["z"]["data"]["url"]
            else:
                thumbnail_src = img_src
        except (KeyError, TypeError):
            thumbnail_src = img_src

        if "ownerNsid" not in photo:
            url = img_src
        else:
            url = build_flickr_url(photo["ownerNsid"], photo.get("id", ""))

        results.append({
            "url": url,
            "img_src": img_src,
            "thumbnail_src": thumbnail_src,
            "source": source,
            "resolution": resolution,
            "template": "images.html",
            "author": author,
            "title": title,
            "content": content,
        })

    return results
