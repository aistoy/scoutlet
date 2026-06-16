"""PubMed biomedical literature search - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* -> from scoutlet.*
- Removed TYPE_CHECKING blocks and res.types.Paper (return plain dict)
- request() still does sync esearch -> efetch (2-step); requires scoutlet.network.get
"""

import logging
from datetime import datetime
from urllib.parse import urlencode

from lxml import etree

from scoutlet.network import get
from scoutlet.utils import eval_xpath_getindex, eval_xpath_list, extract_text

logger = logging.getLogger("scoutlet.engines.pubmed")

about = {
    "website": "https://www.ncbi.nlm.nih.gov/pubmed/",
    "wikidata_id": "Q1540899",
    "official_api_documentation": {
        "url": "https://www.ncbi.nlm.nih.gov/home/develop/api/",
        "comment": "More info on api: https://www.ncbi.nlm.nih.gov/books/NBK25501/",
    },
    "use_official_api": True,
    "require_api_key": False,
    "results": "XML",
}

categories = ["science", "scientific publications"]

eutils_api = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
number_of_results = 10
pubmed_url = "https://www.ncbi.nlm.nih.gov/pubmed/"


def request(query, params):
    args = urlencode({
        "db": "pubmed",
        "term": query,
        "retstart": (params["pageno"] - 1) * number_of_results,
        "hits": number_of_results,
    })
    esearch_url = f"{eutils_api}/esearch.fcgi?{args}"
    esearch_resp = get(esearch_url, timeout=3)
    pmids_results = etree.XML(esearch_resp.content)
    pmids = [i.text for i in pmids_results.xpath("//eSearchResult/IdList/Id") if i.text]

    args = urlencode({
        "db": "pubmed",
        "retmode": "xml",
        "id": ",".join(pmids),
    })
    efetch_url = f"{eutils_api}/efetch.fcgi?{args}"
    params["url"] = efetch_url


def response(resp):
    efetch_xml = etree.XML(resp.content)
    results = []

    def _field_txt(xml, xpath_str):
        elem = eval_xpath_getindex(xml, xpath_str, 0, default="")
        return extract_text(elem, allow_none=True) or ""

    for pubmed_article in eval_xpath_list(efetch_xml, "//PubmedArticle"):
        medline_citation = eval_xpath_getindex(pubmed_article, "./MedlineCitation", 0)
        pubmed_data = eval_xpath_getindex(pubmed_article, "./PubmedData", 0, default=None)

        title_elem = eval_xpath_getindex(medline_citation, ".//Article/ArticleTitle", 0, default=None)
        pmid_elem = eval_xpath_getindex(medline_citation, ".//PMID", 0, default=None)
        title = title_elem.text if title_elem is not None and title_elem.text else ""
        pmid = pmid_elem.text if pmid_elem is not None and pmid_elem.text else ""
        url = pubmed_url + pmid

        content = _field_txt(medline_citation, ".//Abstract/AbstractText//text()")
        doi = _field_txt(medline_citation, ".//ELocationID[@EIdType='doi']/text()")
        journal = _field_txt(medline_citation, "./Article/Journal/Title/text()")
        issn = _field_txt(medline_citation, "./Article/Journal/ISSN/text()")

        authors = []
        for author in eval_xpath_list(medline_citation, "./Article/AuthorList/Author"):
            f = eval_xpath_getindex(author, "./ForeName", 0, default=None)
            l = eval_xpath_getindex(author, "./LastName", 0, default=None)
            f_text = f.text if f is not None and f.text else ""
            l_text = l.text if l is not None and l.text else ""
            name = f"{f_text} {l_text}".strip()
            if name:
                authors.append(name)

        pub_date = None
        if pubmed_data is not None:
            accepted_date = eval_xpath_getindex(
                pubmed_data, "./History//PubMedPubDate[@PubStatus='accepted']", 0, default=None
            )
            if accepted_date is not None:
                year_elem = eval_xpath_getindex(accepted_date, "./Year", 0, default=None)
                month_elem = eval_xpath_getindex(accepted_date, "./Month", 0, default=None)
                day_elem = eval_xpath_getindex(accepted_date, "./Day", 0, default=None)
                try:
                    year = int(year_elem.text) if year_elem is not None else 0
                    month = int(month_elem.text) if month_elem is not None else 0
                    day = int(day_elem.text) if day_elem is not None else 0
                    if year and month and day:
                        pub_date = datetime(year=year, month=month, day=day)
                except (ValueError, TypeError):
                    pass

        content_parts = []
        if content:
            content_parts.append(" ".join(content.split()))
        if journal:
            content_parts.append("Journal: " + journal)
        if authors:
            content_parts.append("Authors: " + ", ".join(authors))
        if doi:
            content_parts.append("DOI: " + doi)

        results.append({
            "template": "paper.html",
            "url": url,
            "title": " ".join(title.split()) if title else "",
            "content": " | ".join(content_parts),
            "publishedDate": pub_date,
            "doi": doi,
            "authors": authors,
            "journal": journal,
            "issn": [issn] if issn else [],
        })

    return results
