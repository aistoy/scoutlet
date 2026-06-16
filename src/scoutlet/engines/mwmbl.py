"""Mwmbl - adapted from SearXNG.

Changes:
- from searx.* -> from scoutlet.*
- Removed fetch_traits
- Removed TYPE_CHECKING guard blocks
- Use plain dicts instead of MainResult/LegacyResult

Mwmbl is a non-profit, ad-free, free-libre and free-lunch search engine with
a focus on useability and speed.  At the moment it is little more than an idea
together with a proof of concept implementation of the web front-end and search
technology on a small index.

Mwmbl does not support regions, languages, safe-search or time range.

https://github.com/mwmbl/mwmbl
"""

import logging
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.mwmbl")

about = {
    "website": 'https://github.com/mwmbl/mwmbl',
    "use_official_api": True,
    "require_api_key": False,
    "results": 'JSON',
}

paging = False
categories = ['general']

api_url = "https://api.mwmbl.org/api/v1"


def request(query, params):
    params['url'] = f"{api_url}/search/?{urlencode({'s': query})}"
    return params


def response(resp):
    results = []
    json_results = resp.json()

    for result in json_results:
        title_parts = [title['value'] for title in result.get('title', [])]
        extract_parts = [extract['value'] for extract in result.get('extract', [])]
        results.append({
            'url': result.get('url', ''),
            'title': ''.join(title_parts),
            'content': ''.join(extract_parts),
        })

    return results
