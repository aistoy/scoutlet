"""SoundCloud (music) - adapted from SearXNG.

Changes:
- Removed EngineCache; client_id cached in module-global (no expiry, refresh on demand)
- from searx.network.get -> from scoutlet.network.get
- Replaced dateutil.parser with datetime.fromisoformat
"""

import logging
import re
import datetime
from urllib.parse import quote_plus, urlencode

from lxml import html

from scoutlet.network import get as http_get

logger = logging.getLogger("scoutlet.engines.soundcloud")

about = {
    "website": "https://soundcloud.com",
    "wikidata_id": "Q568769",
    "official_api_documentation": "https://developers.soundcloud.com/docs/api/guide",
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["music"]
paging = True

search_url = "https://api-v2.soundcloud.com/search"

cid_re = re.compile(r'client_id:"([^"]*)"', re.I | re.U)
results_per_page = 10
soundcloud_facet = "model"

app_locale_map = {
    "de": "de", "en": "en", "es": "es", "fr": "fr", "oc": "fr",
    "it": "it", "nl": "nl", "pl": "pl", "szl": "pl", "pt": "pt_BR",
    "pap": "pt_BR", "sv": "sv",
}

# Module-global client_id cache
_guest_client_id: str | None = None


def get_client_id():
    global _guest_client_id
    if _guest_client_id:
        return _guest_client_id

    url = "https://soundcloud.com"
    try:
        resp = http_get(url, timeout=3)
    except Exception:
        logger.exception("Failed to fetch soundcloud homepage")
        return None

    if not getattr(resp, "ok", False):
        logger.error("init: GET %s failed", url)
        return None

    tree = html.fromstring(resp.content)
    script_tags = tree.xpath("//script[contains(@src, '/assets/')]")
    app_js_urls = [tag.get("src") for tag in script_tags if tag is not None]

    client_id = ""
    for js_url in app_js_urls[::-1]:
        try:
            resp = http_get(js_url)
        except Exception:
            continue
        if not getattr(resp, "ok", False):
            continue
        body = resp.content.decode(errors="ignore") if hasattr(resp, "content") else ""
        cids = cid_re.search(body)
        if cids and cids.groups():
            client_id = cids.groups()[0]
            break

    if client_id:
        logger.info("using client_id '%s' for soundcloud queries", client_id)
        _guest_client_id = client_id
        return client_id

    logger.warning("missing valid client_id for soundcloud queries")
    return None


def request(query, params):
    guest_client_id = get_client_id()
    if not guest_client_id:
        # soundcloud.com no longer exposes the guest client_id via the old
        # scrape path; without it the API returns 401. Skip rather than
        # issue a doomed request.
        logger.warning("soundcloud: no client_id available, skipping query")
        return None

    args = {
        "q": query,
        "offset": (params["pageno"] - 1) * results_per_page,
        "limit": results_per_page,
        "facet": soundcloud_facet,
        "client_id": guest_client_id,
        "app_locale": app_locale_map.get((params.get("language") or "en").split("-")[0], "en"),
    }
    params["url"] = f"{search_url}?{urlencode(args)}"
    return params


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def response(resp):
    results = []
    data = resp.json()

    for result in data.get("collection", []):
        if result.get("kind") not in ("track", "playlist"):
            continue
        url = result.get("permalink_url")
        if not url:
            continue
        uri = quote_plus(result.get("uri", ""))

        content_parts = []
        if result.get("description"):
            content_parts.append(result["description"])
        if result.get("label_name"):
            content_parts.append(result["label_name"])

        user = result.get("user") or {}
        thumbnail = result.get("artwork_url") or user.get("avatar_url") or ""

        length = None
        duration = result.get("duration", 0)
        if duration:
            try:
                length = datetime.timedelta(seconds=int(duration) / 1000)
            except (ValueError, TypeError):
                pass

        results.append({
            "url": url,
            "title": result.get("title", ""),
            "content": " / ".join(content_parts),
            "publishedDate": _parse_date(result.get("last_modified")),
            "iframe_src": "https://w.soundcloud.com/player/?url=" + uri,
            "views": result.get("playback_count", 0) or None,
            "thumbnail": thumbnail or None,
            "length": length,
            "author": user.get("full_name"),
        })

    return results
