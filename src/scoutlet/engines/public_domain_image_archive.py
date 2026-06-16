"""Public Domain Image Archive - adapted from SearXNG.

Changes:
- Module-global cached API URL instead of EngineCache
"""

import logging
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl
from json import dumps

from scoutlet.network import get
from scoutlet.utils import extr
from scoutlet.exceptions import SearchEngineAccessDeniedException, SearchException

logger = logging.getLogger("scoutlet.engines.public_domain_image_archive")

THUMBNAIL_SUFFIX = "?fit=max&h=360&w=360"

about = {
    "website": "https://pdimagearchive.org",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

pdia_base_url = "https://pdimagearchive.org"
pdia_config_start = "/_astro/InfiniteSearch."
pdia_config_end = ".js"
categories = ["images"]
page_size = 20
paging = True

_cached_api_url: str | None = None


def _clean_url(url):
    parsed = urlparse(url)
    query = [(k, v) for (k, v) in parse_qsl(parsed.query) if k not in ["ixid", "s"]]
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(query), parsed.fragment))


def _get_algolia_api_url():
    global _cached_api_url

    if _cached_api_url:
        return _cached_api_url

    resp = get(f"{pdia_base_url}/search/?q=", timeout=3)
    if resp.status_code != 200:
        raise LookupError("Failed to fetch config location for PDImageArchive")
    pdia_config_filepart = extr(resp.text, pdia_config_start, pdia_config_end)
    pdia_config_url = pdia_base_url + pdia_config_start + pdia_config_filepart + pdia_config_end

    resp = get(pdia_config_url)
    if resp.status_code != 200:
        raise LookupError("Failed to obtain AWS api url for PDImageArchive")

    api_url = extr(resp.text, 'const r="', '"', default=None)
    if api_url is None:
        raise LookupError("Couldn't obtain AWS api url for PDImageArchive")

    _cached_api_url = api_url
    return api_url


def _clear_cached_api_url():
    global _cached_api_url
    _cached_api_url = None


def request(query, params):
    try:
        api_url = _get_algolia_api_url()
    except LookupError as e:
        # Site changed how the Algolia endpoint is exposed; without the URL
        # we can't issue the search. Return None so the engine degrades
        # gracefully instead of crashing the whole search run.
        logger.warning("PDImageArchive: %s", e)
        return None

    params["url"] = api_url
    params["method"] = "POST"

    request_data = {
        "page": params["pageno"] - 1,
        "query": query,
        "hitsPerPage": page_size,
        "indexName": "prod_all-images",
    }
    params["headers"] = {"Content-Type": "application/json"}
    params["data"] = dumps(request_data)
    params["raise_for_httperror"] = False
    return params


def response(resp):
    results = []
    json_data = resp.json()

    if resp.status_code == 403:
        _clear_cached_api_url()
        raise SearchEngineAccessDeniedException()

    if resp.status_code != 200:
        raise SearchException(f"PDImageArchive HTTP {resp.status_code}")

    if "results" not in json_data:
        return []

    for result in (json_data.get("results") or [{}])[0].get("hits", []):
        content = []
        if result.get("themes"):
            content.append("Themes: " + str(result["themes"]))
        if result.get("encompassingWork"):
            content.append("Encompassing work: " + str(result["encompassingWork"]))

        base_image_url = (result.get("thumbnail") or "").split("?")[0]

        results.append({
            "template": "images.html",
            "url": _clean_url(f"{about['website']}/images/{result.get('objectID', '')}"),
            "img_src": _clean_url(base_image_url),
            "thumbnail_src": _clean_url(base_image_url + THUMBNAIL_SUFFIX),
            "title": "%s by %s %s" % (
                (result.get("title") or "").strip(),
                result.get("artist", ""),
                result.get("displayYear", ""),
            ),
            "content": "\n".join(content),
        })

    return results
