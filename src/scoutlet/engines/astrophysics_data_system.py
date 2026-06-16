"""NASA Astrophysics Data System (ADS) - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* -> from scoutlet.*
- Removed TYPE_CHECKING blocks and res.types.Paper (return plain dict)

Requires an API key. Set via engine config:
    load_engines(engine_configs={"astrophysics_data_system": {"api_key": "..."}})
"""

import logging
from datetime import datetime
from urllib.parse import urlencode

from scoutlet.exceptions import SearchEngineAPIException
from scoutlet.utils import html_to_text

logger = logging.getLogger("scoutlet.engines.astrophysics_data_system")

about = {
    "website": "https://ui.adsabs.harvard.edu/",
    "wikidata_id": "Q752099",
    "official_api_documentation": "https://ui.adsabs.harvard.edu/help/api/api-docs.html",
    "use_official_api": True,
    "require_api_key": True,
    "results": "JSON",
}

categories = ["science", "scientific publications"]
paging = True
base_url = "https://api.adsabs.harvard.edu/v1/search/query"

api_key = "unset"

ads_field_list = [
    "abstract", "author", "bibcode", "comment", "date", "doi",
    "isbn", "issn", "keyword", "page", "page_count", "page_range",
    "pub", "pubdate", "pubnote", "read_count", "title", "volume", "year",
]
ads_rows = 10
ads_sort = "read_count desc"


def setup(engine_settings):
    # api_key is a module-level attribute; engine_configs override is applied
    # via setattr before setup() runs (see engine_loader.load_engine).
    if api_key and api_key not in ("unset", "unknown", "..."):
        return True
    logger.error("Astrophysics Data System (ADS) API key is not set or invalid.")
    return False


def request(query, params):
    args = {
        "q": query,
        "fl": ",".join(ads_field_list),
        "rows": ads_rows,
        "start": ads_rows * (params["pageno"] - 1),
    }
    if ads_sort:
        args["sort"] = ads_sort

    params["headers"]["Authorization"] = f"Bearer {api_key}"
    params["url"] = f"{base_url}?{urlencode(args)}"


def response(resp):
    results = []
    json_data = resp.json()

    if "error" in json_data:
        raise SearchEngineAPIException(json_data["error"].get("msg", "ADS API error"))

    for doc in json_data.get("response", {}).get("docs", []):
        def _str(k):
            return str(doc.get(k, "") or "")

        def _list(k):
            return doc.get(k, []) or []

        authors = _list("author")
        if len(authors) > 15:
            authors = authors[:15] + ["et al."]

        bibcode = _str("bibcode")
        url = f"https://ui.adsabs.harvard.edu/abs/{bibcode}/" if bibcode else ""
        title = html_to_text(_list("title")[0]) if _list("title") else ""
        abstract = html_to_text(_str("abstract"))
        doi_list = _list("doi")
        doi = doi_list[0] if doi_list else ""

        publishedDate = None
        date_str = _str("date")
        if date_str:
            try:
                publishedDate = datetime.fromisoformat(date_str)
            except ValueError:
                pass

        content_parts = []
        if abstract:
            content_parts.append(abstract)
        if authors:
            content_parts.append("Authors: " + ", ".join(authors))
        publisher = _str("pub") + " " + _str("year")
        if publisher.strip():
            content_parts.append("Published in: " + publisher.strip())
        pubnote = _list("pubnote")
        if pubnote:
            content_parts.append(" / ".join(pubnote))

        results.append({
            "template": "paper.html",
            "url": url,
            "title": title,
            "content": " | ".join(content_parts),
            "publishedDate": publishedDate,
            "doi": doi,
            "authors": authors,
            "issn": _list("issn"),
            "isbn": _list("isbn"),
            "tags": _list("keyword"),
            "pages": ",".join(_list("page")),
            "publisher": publisher.strip(),
            "volume": _str("volume"),
            "comments": " / ".join(_list("pubnote")),
        })

    return results
