"""Semantic Scholar academic search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* -> from scoutlet.*
- Removed EngineCache + get_ui_version() (skip X-S2-UI-Version header; works without it in most cases)
- Removed flask_babel and TYPE_CHECKING blocks
- Return plain dict instead of res.types.Paper
"""

import logging
from datetime import datetime

from scoutlet.utils import html_to_text

logger = logging.getLogger("scoutlet.engines.semantic_scholar")

about = {
    "website": "https://www.semanticscholar.org/",
    "wikidata_id": "Q22908627",
    "official_api_documentation": "https://api.semanticscholar.org/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["science", "scientific publications"]
paging = True
search_url = "https://www.semanticscholar.org/api/1/search"
base_url = "https://www.semanticscholar.org"


def request(query, params):
    params["url"] = search_url
    params["method"] = "POST"
    params["headers"].update({
        "Content-Type": "application/json",
        "X-S2-Client": "webapp-browser",
    })
    params["json"] = {
        "queryString": query,
        "page": params["pageno"],
        "pageSize": 10,
        "sort": "relevance",
        "getQuerySuggestions": False,
        "authors": [],
        "coAuthors": [],
        "venues": [],
        "performTitleMatch": True,
    }


def response(resp):
    results = []
    json_data = resp.json()

    for result in json_data.get("results", []):
        url = (result.get("primaryPaperLink") or {}).get("url")
        if not url and result.get("links"):
            url = result.get("links")[0]
        if not url:
            alternatePaperLinks = result.get("alternatePaperLinks")
            if alternatePaperLinks:
                url = alternatePaperLinks[0].get("url")
        if not url:
            url = base_url + "/paper/%s" % result.get("id", "")

        publishedDate = None
        if "pubDate" in result:
            try:
                publishedDate = datetime.strptime(result["pubDate"], "%Y-%m-%d")
            except ValueError:
                pass

        authors = []
        for author in result.get("authors", []):
            try:
                authors.append(author[0]["name"])
            except (IndexError, KeyError, TypeError):
                continue

        pdf_url = ""
        for doc in result.get("alternatePaperLinks", []):
            if doc.get("linkType") not in ("crawler", "doi"):
                pdf_url = doc.get("url", "")
                break

        comments = ""
        if "citationStats" in result:
            stats = result["citationStats"]
            comments = "{numCitations} citations from {first} to {last}".format(
                numCitations=stats.get("numCitations", 0),
                first=stats.get("firstCitationVelocityYear", ""),
                last=stats.get("lastCitationVelocityYear", ""),
            )

        title = ""
        if isinstance(result.get("title"), dict):
            title = result["title"].get("text", "")
        elif isinstance(result.get("title"), str):
            title = result["title"]

        abstract = ""
        if isinstance(result.get("paperAbstract"), dict):
            abstract = html_to_text(result["paperAbstract"].get("text", ""))
        elif isinstance(result.get("paperAbstract"), str):
            abstract = result["paperAbstract"]

        venue = ""
        if isinstance(result.get("venue"), dict):
            venue = result["venue"].get("text") or ""
        if not venue and isinstance(result.get("journal"), dict):
            venue = result["journal"].get("name") or ""

        doi = (result.get("doiInfo") or {}).get("doi", "")

        content_parts = []
        if abstract:
            content_parts.append(abstract)
        if venue:
            content_parts.append("Venue: " + venue)
        if authors:
            content_parts.append("Authors: " + ", ".join(authors))
        if comments:
            content_parts.append(comments)

        results.append({
            "template": "paper.html",
            "url": url,
            "title": title,
            "content": " | ".join(content_parts),
            "publishedDate": publishedDate,
            "doi": doi,
            "authors": authors,
            "journal": venue,
            "tags": result.get("fieldsOfStudy") or [],
            "pdf_url": pdf_url,
            "comments": comments,
        })

    return results
