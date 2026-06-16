"""Crossref scholarly metadata search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* -> from scoutlet.*
- Removed TYPE_CHECKING blocks and res.types.Paper (return plain dict)
"""

import logging
from urllib.parse import urlencode
from datetime import datetime

logger = logging.getLogger("scoutlet.engines.crossref")

about = {
    "website": "https://www.crossref.org/",
    "wikidata_id": "Q5188229",
    "official_api_documentation": "https://api.crossref.org/swagger-ui/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["science", "scientific publications"]
paging = True
search_url = "https://api.crossref.org/works"


def request(query, params):
    args = {
        "query": query,
        "offset": 20 * (params["pageno"] - 1),
    }
    params["url"] = f"{search_url}?{urlencode(args)}"


def response(resp):
    results = []
    json_data = resp.json()

    for record in json_data["message"]["items"]:

        if record["type"] == "component":
            continue

        title = ""
        journal = ""

        if record["type"] == "book-chapter":
            title = record["container-title"][0]
            if record["title"][0].lower().strip() != title.lower().strip():
                title += f" ({record['title'][0]})"
        else:
            title = record["title"][0] if "title" in record else record.get("container-title", [None])[0]
            journal = record.get("container-title", [None])[0] if "title" in record else ""

        doi = str(record.get("DOI", "") or "")
        url = str(record.get("URL", "") or "")
        content = str(record.get("abstract", "") or "")

        if "resource" in record and "primary" in record["resource"] and "URL" in record["resource"]["primary"]:
            url = record["resource"]["primary"]["URL"]

        publishedDate = None
        if "published" in record and "date-parts" in record["published"]:
            try:
                parts = record["published"]["date-parts"][0]
                padded = (parts + [1, 1, 1])[:3]
                publishedDate = datetime(*padded)
            except (ValueError, TypeError):
                pass

        authors = [
            (a.get("given", "") + " " + a.get("family", "")).strip()
            for a in record.get("author", [])
        ]

        content_parts = []
        if content:
            content_parts.append(" ".join(content.split()))
        if journal:
            content_parts.append("Journal: " + journal)
        if authors:
            content_parts.append("Authors: " + ", ".join(authors))

        results.append({
            "template": "paper.html",
            "url": url,
            "title": title or "",
            "content": " | ".join(content_parts),
            "publishedDate": publishedDate,
            "doi": doi,
            "authors": authors,
            "journal": journal,
            "tags": record.get("subject") or [],
            "publisher": str(record.get("publisher", "") or ""),
            "volume": str(record.get("volume", "") or ""),
            "pages": str(record.get("page", "") or ""),
            "type": str(record.get("type", "") or ""),
        })

    return results
