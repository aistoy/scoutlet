"""OpenAlex scholarly works API - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* -> from scoutlet.*
- Removed TYPE_CHECKING blocks and res.types.Paper (return plain dict)
"""

import logging
from datetime import datetime
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.openalex")

about = {
    "website": "https://openalex.org/",
    "wikidata_id": "Q110718454",
    "official_api_documentation": "https://docs.openalex.org/how-to-use-the-api/api-overview",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["science", "scientific publications"]
paging = True
search_url = "https://api.openalex.org/works"

mailto = ""


def request(query, params):
    args = {
        "search": query,
        "page": params["pageno"],
        "per-page": 10,
        "sort": "relevance_score:desc",
    }

    language = params.get("language")
    filters = []
    if isinstance(language, str) and language != "all":
        iso2 = language.split("-")[0].split("_")[0]
        if len(iso2) == 2:
            filters.append(f"language:{iso2}")

    if filters:
        args["filter"] = ",".join(filters)

    if isinstance(mailto, str) and mailto != "":
        args["mailto"] = mailto

    params["url"] = f"{search_url}?{urlencode(args)}"


def _stringify_pages(biblio):
    first_page = biblio.get("first_page")
    last_page = biblio.get("last_page")
    if first_page and last_page:
        return f"{first_page}-{last_page}"
    if first_page:
        return str(first_page)
    if last_page:
        return str(last_page)
    return ""


def _parse_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _doi_to_plain(doi_value):
    if not doi_value:
        return ""
    return doi_value.removeprefix("https://doi.org/")


def _reconstruct_abstract(abstract_inverted_index):
    if not abstract_inverted_index:
        return None
    position_to_token = {}
    max_index = -1
    for token, positions in abstract_inverted_index.items():
        for pos in positions:
            position_to_token[pos] = token
            max_index = max(max_index, pos)
    if max_index < 0:
        return None
    ordered_tokens = [position_to_token.get(i, "") for i in range(0, max_index + 1)]
    text = " ".join(t for t in ordered_tokens if t != "")
    return text if text != "" else None


def _extract_links(item):
    primary_location = item.get("primary_location", {}) or {}
    open_access = item.get("open_access", {}) or {}

    landing_page_url = primary_location.get("landing_page_url") or ""
    work_url = item.get("id", "")

    url = landing_page_url or work_url
    html_url = landing_page_url
    pdf_url = primary_location.get("pdf_url") or open_access.get("oa_url") or ""

    return url, html_url, pdf_url


def _extract_authors(item):
    authors = []
    for auth in item.get("authorships", []):
        if not auth:
            continue
        author_obj = auth.get("author", {}) or {}
        display_name = author_obj.get("display_name")
        if isinstance(display_name, str) and display_name != "":
            authors.append(display_name)
    return authors


def _extract_tags(item):
    tags = []
    for c in item.get("concepts", []):
        name = (c or {}).get("display_name")
        if isinstance(name, str) and name != "":
            tags.append(name)
    return tags


def _extract_biblio(item):
    host_venue = item.get("host_venue", {}) or {}
    biblio = item.get("biblio", {}) or {}

    journal = host_venue.get("display_name", "") or ""
    publisher = host_venue.get("publisher", "") or ""
    pages = _stringify_pages(biblio)
    volume = biblio.get("volume", "") or ""
    number = biblio.get("issue", "") or ""
    published_date = _parse_date(item.get("publication_date"))
    return journal, publisher, pages, volume, number, published_date


def _extract_comments(item):
    cited_by_count = item.get("cited_by_count")
    if isinstance(cited_by_count, int):
        return f"{cited_by_count} citations"
    return ""


def response(resp):
    data = resp.json()
    results = []

    for item in data.get("results", []):
        url, html_url, pdf_url = _extract_links(item)
        title = item.get("title", "") or ""
        content = _reconstruct_abstract(item.get("abstract_inverted_index")) or ""
        authors = _extract_authors(item)
        journal, publisher, pages, volume, number, published_date = _extract_biblio(item)
        doi = _doi_to_plain(item.get("doi"))
        tags = _extract_tags(item)
        comments = _extract_comments(item)

        content_parts = []
        if content:
            content_parts.append(content)
        if journal:
            content_parts.append("Journal: " + journal)
        if authors:
            content_parts.append("Authors: " + ", ".join(authors))
        if comments:
            content_parts.append(comments)

        results.append({
            "template": "paper.html",
            "url": url,
            "title": title,
            "content": " | ".join(content_parts),
            "publishedDate": published_date,
            "doi": doi,
            "authors": authors,
            "journal": journal,
            "publisher": publisher,
            "tags": tags,
            "pdf_url": pdf_url,
            "pages": pages,
            "volume": volume,
            "number": number,
            "type": item.get("type") or "",
            "comments": comments,
        })

    return results
