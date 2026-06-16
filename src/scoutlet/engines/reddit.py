"""Reddit - adapted from SearXNG.

Changes:
- from searx.* -> from scoutlet.*
- Removed fetch_traits
- Removed TYPE_CHECKING guard blocks
- Use plain dicts instead of MainResult/LegacyResult
"""

import json
import logging
from datetime import datetime
from urllib.parse import urlencode, urljoin, urlparse

logger = logging.getLogger("scoutlet.engines.reddit")

about = {
    "website": 'https://www.reddit.com/',
    "wikidata_id": 'Q1136',
    "official_api_documentation": 'https://www.reddit.com/dev/api',
    "use_official_api": True,
    "require_api_key": False,
    "results": 'JSON',
}

categories = ['social media']
page_size = 25

base_url = 'https://www.reddit.com/'
search_url = base_url + 'search.json?{query}'


def request(query, params):
    query = urlencode({'q': query, 'limit': page_size})
    params['url'] = search_url.format(query=query)
    return params


def response(resp):
    img_results = []
    text_results = []
    search_results = json.loads(resp.text)

    if 'data' not in search_results:
        return []

    posts = search_results.get('data', {}).get('children', [])

    for post in posts:
        data = post['data']
        params = {
            'url': urljoin(base_url, data['permalink']),
            'title': data['title'],
        }

        thumbnail = data['thumbnail']
        url_info = urlparse(thumbnail)

        if url_info[1] != '' and url_info[2] != '':
            params['img_src'] = data['url']
            params['thumbnail_src'] = thumbnail
            params['template'] = 'images.html'
            img_results.append(params)
        else:
            created = datetime.fromtimestamp(data['created_utc'])
            content = data['selftext']
            if len(content) > 500:
                content = content[:500] + '...'
            params['content'] = content
            params['publishedDate'] = created
            text_results.append(params)

    return img_results + text_results
