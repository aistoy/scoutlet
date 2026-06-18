"""Yahoo Search - adapted from SearXNG.

Changes:
- from searx.* -> from scoutlet.*
- Removed fetch_traits
- Removed TYPE_CHECKING guard blocks
- Use plain dicts instead of MainResult/LegacyResult
"""

import logging
from urllib.parse import unquote, urlencode

from lxml import html

from scoutlet.utils import eval_xpath_getindex, eval_xpath_list, extract_text, html_to_text

logger = logging.getLogger("scoutlet.engines.yahoo")

about = {
    "website": 'https://search.yahoo.com/',
    "wikidata_id": None,
    "official_api_documentation": 'https://developer.yahoo.com/api/',
    "use_official_api": False,
    "require_api_key": False,
    "results": 'HTML',
}

categories = ['general', 'web']
paging = True
time_range_support = True

time_range_dict = {'day': 'd', 'week': 'w', 'month': 'm'}
safesearch_dict = {0: 'p', 1: 'i', 2: 'r'}

region2domain = {
    "CO": "co.search.yahoo.com", "TH": "th.search.yahoo.com",
    "VE": "ve.search.yahoo.com", "CL": "cl.search.yahoo.com",
    "HK": "hk.search.yahoo.com", "PE": "pe.search.yahoo.com",
    "CA": "ca.search.yahoo.com", "DE": "de.search.yahoo.com",
    "FR": "fr.search.yahoo.com", "TW": "tw.search.yahoo.com",
    "GB": "uk.search.yahoo.com", "UK": "uk.search.yahoo.com",
    "BR": "br.search.yahoo.com", "IN": "in.search.yahoo.com",
    "ES": "espanol.search.yahoo.com", "PH": "ph.search.yahoo.com",
    "AR": "ar.search.yahoo.com", "MX": "mx.search.yahoo.com",
    "SG": "sg.search.yahoo.com",
}

lang2domain = {
    'zh_chs': 'hk.search.yahoo.com', 'zh_cht': 'tw.search.yahoo.com',
    'any': 'search.yahoo.com', 'en': 'search.yahoo.com',
    'bg': 'search.yahoo.com', 'cs': 'search.yahoo.com',
    'da': 'search.yahoo.com', 'el': 'search.yahoo.com',
    'et': 'search.yahoo.com', 'he': 'search.yahoo.com',
    'hr': 'search.yahoo.com', 'ja': 'search.yahoo.com',
    'ko': 'search.yahoo.com', 'sk': 'search.yahoo.com',
    'sl': 'search.yahoo.com',
}

yahoo_languages = {
    "all": "any", "ar": "ar", "bg": "bg", "cs": "cs", "da": "da",
    "de": "de", "el": "el", "en": "en", "es": "es", "et": "et",
    "fi": "fi", "fr": "fr", "he": "he", "hr": "hr", "hu": "hu",
    "it": "it", "ja": "ja", "ko": "ko", "lt": "lt", "lv": "lv",
    "nl": "nl", "no": "no", "pl": "pl", "pt": "pt", "ro": "ro",
    "ru": "ru", "sk": "sk", "sl": "sl", "sv": "sv", "th": "th",
    "tr": "tr", "zh": "zh_chs", "zh_Hans": "zh_chs", "zh-CN": "zh_chs",
    "zh_Hant": "zh_cht", "zh-HK": "zh_cht", "zh-TW": "zh_cht",
}


def build_sb_cookie(cookie_params):
    return "&".join(f"{k}={v}" for k, v in cookie_params.items())


def request(query, params):
    lang = params.get("language", "all").split("-")[0]
    lang = yahoo_languages.get(lang, "any")

    url_params = {'p': query}
    btf = time_range_dict.get(params.get('time_range'))
    if btf:
        url_params['btf'] = btf

    if params['pageno'] == 1:
        url_params['iscqry'] = ''
    elif params['pageno'] >= 2:
        url_params['b'] = params['pageno'] * 7 + 1
        url_params['pz'] = 7
        url_params['bct'] = 0
        url_params['xargs'] = 0

    sbcookie_params = {
        'v': 1, 'vm': safesearch_dict[params.get('safesearch', 0)],
        'fl': 1, 'vl': f'lang_{lang}', 'pn': 10, 'rw': 'new', 'userset': 1,
    }
    params['cookies']['sB'] = build_sb_cookie(sbcookie_params)

    region = params.get("language", "all").split("-")[-1] if "-" in params.get("language", "all") else None
    domain = region2domain.get(region)
    if not domain:
        domain = lang2domain.get(lang, f'{lang}.search.yahoo.com')

    params['url'] = f'https://{domain}/search?{urlencode(url_params)}'
    params['domain'] = domain


def parse_url(url_string):
    endings = ['/RS', '/RK']
    endpositions = []
    start = url_string.find('http', url_string.find('/RU=') + 1)
    for ending in endings:
        endpos = url_string.rfind(ending)
        if endpos > -1:
            endpositions.append(endpos)
    if start == 0 or len(endpositions) == 0:
        return url_string
    end = min(endpositions)
    return unquote(url_string[start:end])


def response(resp):
    results = []
    dom = html.fromstring(resp.text)

    url_xpath = './/div[contains(@class,"compTitle")]/h3/a/@href'
    title_xpath = './/h3//a/@aria-label'

    domain = getattr(resp, 'search_params', {}).get('domain', 'search.yahoo.com')
    if domain == "search.yahoo.com":
        url_xpath = './/div[contains(@class,"compTitle")]/a/@href'
        title_xpath = './/div[contains(@class,"compTitle")]/a/h3/span'

    for result in eval_xpath_list(dom, '//div[contains(@class,"algo-sr")]'):
        url = eval_xpath_getindex(result, url_xpath, 0, default=None)
        if url is None:
            continue
        url = parse_url(url)
        title = eval_xpath_getindex(result, title_xpath, 0, default='')
        title = extract_text(title)
        content = eval_xpath_getindex(result, './/div[contains(@class, "compText")]', 0, default='')
        content = extract_text(content, allow_none=True)

        results.append({
            'url': url,
            'title': " ".join(html_to_text(title).strip().split()),
            'content': " ".join(html_to_text(content).strip().split()),
        })

    return results
