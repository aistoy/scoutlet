"""Deezer (Music) - adapted from SearXNG.

Changes:
- from searx.* -> from scoutlet.*
- Removed fetch_traits
- Removed TYPE_CHECKING guard blocks
- Use plain dicts instead of MainResult/LegacyResult
"""

import logging
from json import loads
from urllib.parse import urlencode

logger = logging.getLogger("scoutlet.engines.deezer")

about = {
    "website": 'https://deezer.com',
    "wikidata_id": 'Q602243',
    "official_api_documentation": 'https://developers.deezer.com/',
    "use_official_api": True,
    "require_api_key": False,
    "results": 'JSON',
}

categories = ['music']
paging = True

url = 'https://api.deezer.com/'
search_url = url + 'search?{query}&index={offset}'
iframe_src = "https://www.deezer.com/plugins/player?type=tracks&id={audioid}"


def request(query, params):
    offset = (params['pageno'] - 1) * 25
    params['url'] = search_url.format(query=urlencode({'q': query}), offset=offset)
    return params


def response(resp):
    results = []
    search_res = loads(resp.text)

    for result in search_res.get('data', []):
        if result['type'] == 'track':
            title = result['title']
            track_url = result['link']
            if track_url.startswith('http://'):
                track_url = 'https' + track_url[4:]
            content = '{} - {} - {}'.format(
                result['artist']['name'],
                result['album']['title'],
                result['title'],
            )
            results.append({
                'url': track_url,
                'title': title,
                'iframe_src': iframe_src.format(audioid=result['id']),
                'content': content,
            })

    return results
