"""Piped (YouTube frontend) search engine - adapted from SearXNG.

Changes:
- from searx.* -> from scoutlet.*
- dateutil.parser -> datetime.fromtimestamp
- Removed TYPE_CHECKING blocks
- Simplified _backend_url/_frontend_url to not depend on global engines registry
"""

import time
import random
import logging
import datetime
from urllib.parse import urlencode

from scoutlet.utils import humanize_number

logger = logging.getLogger("scoutlet.engines.piped")

about = {
    "website": 'https://github.com/TeamPiped/Piped/',
    "wikidata_id": 'Q107565255',
    "official_api_documentation": 'https://docs.piped.video/docs/api-documentation/',
    "use_official_api": True,
    "require_api_key": False,
    "results": 'JSON',
}

categories = ["videos"]
paging = True

backend_url: list[str] | str = []
frontend_url: str | None = None

piped_filter = 'videos'


def _get_backend_url() -> str:
    url = backend_url
    if isinstance(url, list):
        url = random.choice(url) if url else ""
    return url


def _get_frontend_url() -> str:
    return frontend_url or "https://piped.video"


def request(query, params):
    backend = _get_backend_url()
    if not backend:
        params["url"] = None
        return

    args = {
        'q': query,
        'filter': piped_filter,
    }

    path = "/search"
    if params['pageno'] > 1:
        nextpage = params.get('engine_data', {}).get('nextpage')
        if nextpage:
            path = "/nextpage/search"
            args['nextpage'] = nextpage

    params["url"] = backend + f"{path}?" + urlencode(args)
    return params


def response(resp):
    results = []

    json_data = resp.json()

    for result in json_data.get("items", []):
        uploaded = result.get("uploaded", -1)

        item = {
            "url": _get_frontend_url() + result.get("url", ""),
            "title": result.get("title", ""),
            "publishedDate": datetime.datetime.fromtimestamp(uploaded / 1000) if uploaded > 0 else None,
            "iframe_src": _get_frontend_url() + '/embed' + result.get("url", ""),
            "views": humanize_number(result.get("views", 0)),
        }
        length = result.get("duration")
        if length:
            item["length"] = datetime.timedelta(seconds=length)

        if piped_filter == 'videos':
            item["template"] = "videos.html"
            item["content"] = result.get("shortDescription", "") or ""
            item["thumbnail"] = result.get("thumbnail", "")

        elif piped_filter == 'music_songs':
            item["template"] = "default.html"
            item["thumbnail"] = result.get("thumbnail", "")
            item["content"] = result.get("uploaderName", "") or ""

        results.append(item)

    nextpage = json_data.get("nextpage")
    if nextpage:
        results.append({
            "engine_data": nextpage,
            "key": "nextpage",
        })
    return results
