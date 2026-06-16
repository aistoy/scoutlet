"""PDBe (Protein Data Bank in Europe) - adapted from SearXNG.

Changes from SearXNG original:
- Removed flask_babel gettext (use plain string formatting)
- No imports from searx.*
"""

import logging
from json import loads

logger = logging.getLogger("scoutlet.engines.pdbe")

about = {
    "website": "https://www.ebi.ac.uk/pdbe",
    "wikidata_id": "Q55823905",
    "official_api_documentation": "https://www.ebi.ac.uk/pdbe/api/doc/search.html",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["science"]

hide_obsolete = False

pdb_unpublished_codes = ['HPUB', 'HOLD', 'PROC', 'WAIT', 'AUTH', 'AUCO', 'REPL', 'POLC', 'REFI', 'TRSF', 'WDRN']
pdbe_solr_url = 'https://www.ebi.ac.uk/pdbe/search/pdb/select?'
pdbe_entry_url = 'https://www.ebi.ac.uk/pdbe/entry/pdb/{pdb_id}'
pdbe_preview_url = 'https://www.ebi.ac.uk/pdbe/static/entry/{pdb_id}_deposited_chain_front_image-200x200.png'


def request(query, params):
    params['url'] = pdbe_solr_url
    params['method'] = 'POST'
    params['data'] = {'q': query, 'wt': "json"}
    return params


def construct_body(result):
    title = result.get('title', '')
    content = "{title} - {authors} {journal} ({volume}) {page} ({year})"

    try:
        if result.get('journal'):
            content = content.format(
                title=result.get('citation_title', ''),
                authors=(result.get('entry_author_list') or [''])[0],
                journal=result.get('journal', ''),
                volume=result.get('journal_volume', ''),
                page=result.get('journal_page', ''),
                year=result.get('citation_year', ''),
            )
        else:
            content = content.format(
                title=result.get('citation_title', ''),
                authors=(result.get('entry_author_list') or [''])[0],
                journal='',
                volume='',
                page='',
                year=result.get('release_year', ''),
            )
        thumbnail = pdbe_preview_url.format(pdb_id=result['pdb_id'])
    except (KeyError, IndexError):
        content = ""
        thumbnail = None

    try:
        thumbnail = pdbe_preview_url.format(pdb_id=result['pdb_id'])
    except KeyError:
        thumbnail = None

    return title, content, thumbnail


def response(resp):
    results = []
    docs = loads(resp.text)['response']['docs']

    for result in docs:
        status = result.get('status', '')
        if status in pdb_unpublished_codes:
            continue
        if hide_obsolete:
            continue
        if status == 'OBS':
            title = f"{result.get('title', '')} (OBSOLETE)"
            try:
                superseded_url = pdbe_entry_url.format(pdb_id=result['superseded_by'])
            except KeyError:
                continue
            content = f"This entry has been superseded by: {superseded_url} ({result.get('superseded_by', '')})"
            thumbnail = None
        else:
            title, content, thumbnail = construct_body(result)

        results.append({
            'url': pdbe_entry_url.format(pdb_id=result['pdb_id']),
            'title': title,
            'content': content,
            'thumbnail': thumbnail,
        })

    return results
