"""arXiv scholarly article search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* -> from scoutlet.*
- Removed TYPE_CHECKING blocks and res.types.Paper (return plain dict)
"""

import logging
from datetime import datetime
from urllib.parse import urlencode

from lxml.etree import XPath

from scoutlet.utils import eval_xpath, eval_xpath_getindex, eval_xpath_list

logger = logging.getLogger("scoutlet.engines.arxiv")

about = {
    "website": "https://arxiv.org",
    "wikidata_id": "Q118398",
    "official_api_documentation": "https://info.arxiv.org/help/api/user-manual.html",
    "use_official_api": True,
    "require_api_key": False,
    "results": "XML-RSS",
}

categories = ["science", "scientific publications"]
paging = True
arxiv_max_results = 10
arxiv_search_prefix = "all"

base_url = "https://export.arxiv.org/api/query"

arxiv_namespaces = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
xpath_entry = XPath("//atom:entry", namespaces=arxiv_namespaces)
xpath_title = XPath(".//atom:title", namespaces=arxiv_namespaces)
xpath_id = XPath(".//atom:id", namespaces=arxiv_namespaces)
xpath_summary = XPath(".//atom:summary", namespaces=arxiv_namespaces)
xpath_author_name = XPath(".//atom:author/atom:name", namespaces=arxiv_namespaces)
xpath_doi = XPath(".//arxiv:doi", namespaces=arxiv_namespaces)
xpath_pdf = XPath(".//atom:link[@title='pdf']", namespaces=arxiv_namespaces)
xpath_published = XPath(".//atom:published", namespaces=arxiv_namespaces)
xpath_journal = XPath(".//arxiv:journal_ref", namespaces=arxiv_namespaces)
xpath_category = XPath(".//atom:category/@term", namespaces=arxiv_namespaces)
xpath_comment = XPath("./arxiv:comment", namespaces=arxiv_namespaces)


def request(query, params):
    args = {
        "search_query": f"{arxiv_search_prefix}:{query}",
        "start": (params["pageno"] - 1) * arxiv_max_results,
        "max_results": arxiv_max_results,
    }
    params["url"] = f"{base_url}?{urlencode(args)}"


def response(resp):
    results = []

    from lxml import etree

    dom = etree.fromstring(resp.content)
    for entry in eval_xpath_list(dom, xpath_entry):

        title_elem = eval_xpath_getindex(entry, xpath_title, 0, default=None)
        id_elem = eval_xpath_getindex(entry, xpath_id, 0, default=None)
        summary_elem = eval_xpath_getindex(entry, xpath_summary, 0, default=None)

        title = title_elem.text if title_elem is not None else ""
        url = id_elem.text if id_elem is not None else ""
        abstract = summary_elem.text if summary_elem is not None else ""

        authors = [a.text for a in eval_xpath_list(entry, xpath_author_name) if a is not None]

        doi_element = eval_xpath_getindex(entry, xpath_doi, 0, default=None)
        doi = "" if doi_element is None else (doi_element.text or "")

        pdf_element = eval_xpath_getindex(entry, xpath_pdf, 0, default=None)
        pdf_url = "" if pdf_element is None else pdf_element.attrib.get("href", "")

        journal_element = eval_xpath_getindex(entry, xpath_journal, 0, default=None)
        journal = "" if journal_element is None else (journal_element.text or "")

        tags = [str(tag) for tag in eval_xpath(entry, xpath_category)]

        comments_elements = eval_xpath_getindex(entry, xpath_comment, 0, default=None)
        comments = "" if comments_elements is None else (comments_elements.text or "")

        published_elem = eval_xpath_getindex(entry, xpath_published, 0, default=None)
        publishedDate = None
        if published_elem is not None and published_elem.text:
            try:
                publishedDate = datetime.strptime(published_elem.text, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                pass

        content_parts = []
        if abstract:
            content_parts.append(" ".join(abstract.split()))
        if authors:
            content_parts.append("Authors: " + ", ".join(authors))
        if journal:
            content_parts.append("Journal: " + journal)
        if comments:
            content_parts.append("Comments: " + " ".join(comments.split()))

        results.append({
            "template": "paper.html",
            "url": url,
            "title": " ".join(title.split()),
            "content": " | ".join(content_parts),
            "publishedDate": publishedDate,
            "doi": doi,
            "authors": authors,
            "journal": journal,
            "tags": tags,
            "pdf_url": pdf_url,
            "comments": comments,
        })

    return results
