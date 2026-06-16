"""Google News search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* -> from scoutlet.*
- Removed fetch_traits function
- Removed import babel, from searx import locales
- Hardcoded the ceid_list and simplified ceid lookup (no babel locale parsing)
- Removed type annotations (SXNG_Response, OnlineParams, TYPE_CHECKING)
- Use plain dicts instead of res.types.MainResult
- Use gen_useragent() instead of searxng_useragent()
- Added logger = logging.getLogger("scoutlet.engines.google_news")
- Return list[dict] from response()
"""

import logging
import base64
from urllib.parse import urlencode

from lxml import html

from scoutlet.utils import (
    eval_xpath,
    eval_xpath_list,
    eval_xpath_getindex,
    extract_text,
)
from scoutlet.engines.google import (
    get_google_info,
    detect_google_sorry,
)

logger = logging.getLogger("scoutlet.engines.google_news")

about = {
    "website": 'https://news.google.com',
    "wikidata_id": 'Q12020',
    "official_api_documentation": 'https://developers.google.com/custom-search',
    "use_official_api": False,
    "require_api_key": False,
    "results": 'HTML',
}

# engine dependent config
categories = ['news']
paging = False
time_range_support = False
# Google-News results are always *SafeSearch*
safesearch = True

# List of region/language combinations supported by Google News.
# Values of the ``ceid`` argument of the Google News REST API.
ceid_list = [
    'AE:ar',
    'AR:es-419',
    'AT:de',
    'AU:en',
    'BD:bn',
    'BE:fr',
    'BE:nl',
    'BG:bg',
    'BR:pt-419',
    'BW:en',
    'CA:en',
    'CA:fr',
    'CH:de',
    'CH:fr',
    'CL:es-419',
    'CN:zh-Hans',
    'CO:es-419',
    'CU:es-419',
    'CZ:cs',
    'DE:de',
    'EG:ar',
    'ES:es',
    'ET:en',
    'FR:fr',
    'GB:en',
    'GH:en',
    'GR:el',
    'HK:zh-Hant',
    'HU:hu',
    'ID:en',
    'ID:id',
    'IE:en',
    'IL:en',
    'IL:he',
    'IN:bn',
    'IN:en',
    'IN:hi',
    'IN:ml',
    'IN:mr',
    'IN:ta',
    'IN:te',
    'IT:it',
    'JP:ja',
    'KE:en',
    'KR:ko',
    'LB:ar',
    'LT:lt',
    'LV:en',
    'LV:lv',
    'MA:fr',
    'MX:es-419',
    'MY:en',
    'NA:en',
    'NG:en',
    'NL:nl',
    'NO:no',
    'NZ:en',
    'PE:es-419',
    'PH:en',
    'PK:en',
    'PL:pl',
    'PT:pt-150',
    'RO:ro',
    'RS:sr',
    'RU:ru',
    'SA:ar',
    'SE:sv',
    'SG:en',
    'SI:sl',
    'SK:sk',
    'SN:fr',
    'TH:th',
    'TR:tr',
    'TW:zh-Hant',
    'TZ:en',
    'UA:ru',
    'UA:uk',
    'UG:en',
    'US:en',
    'US:es-419',
    'VE:es-419',
    'VN:vi',
    'ZA:en',
    'ZW:en',
]

# Build a lookup dict from locale tags (e.g. "en-US") to ceid strings (e.g. "US:en")
_ceid_map: dict[str, str] = {}

# Values to skip (low quality results)
_skip_values = {'ET:en', 'ID:en', 'LV:en'}

# Special overrides for locale-to-ceid mapping
_ceid_locale_overrides: dict[str, str] = {
    'NO:no': 'nb-NO',
}


def _build_ceid_map():
    """Build a mapping from scoutlet locale strings to Google News ceid values."""
    for ceid in ceid_list:
        if ceid in _skip_values:
            continue
        region, lang = ceid.split(':')
        x = lang.split('-')
        base_lang = x[0]

        # Derive a locale tag from the ceid
        override = _ceid_locale_overrides.get(ceid)
        if override:
            locale_tag = override
        else:
            locale_tag = base_lang + '-' + region

        _ceid_map[locale_tag] = ceid


_build_ceid_map()


def _get_ceid(searxng_locale: str) -> str:
    """Look up the ceid for a given searxng locale.

    Tries exact match first, then falls back to language-only match,
    and finally defaults to US:en.
    """
    # Direct lookup
    ceid = _ceid_map.get(searxng_locale)
    if ceid:
        return ceid

    # Try language prefix match (e.g. "en" -> first "en-*" entry)
    if '-' in searxng_locale:
        lang_prefix = searxng_locale.split('-')[0]
        for locale_tag, ceid_val in _ceid_map.items():
            if locale_tag.startswith(lang_prefix + '-'):
                return ceid_val

    # Try just the language
    lang = searxng_locale.split('-')[0] if '-' in searxng_locale else searxng_locale
    for locale_tag, ceid_val in _ceid_map.items():
        if locale_tag.startswith(lang + '-'):
            return ceid_val

    # Default: US English
    return 'US:en'


def request(query, params):
    """Google-News search request"""
    sxng_locale = params.get('searxng_locale', 'en-US')
    ceid = _get_ceid(sxng_locale)

    google_info = get_google_info(params, traits)
    google_info['subdomain'] = 'news.google.com'  # google news has only one domain

    ceid_region, ceid_lang = ceid.split(':')
    ceid_parts = ceid_lang.split('-') + [None]
    ceid_lang_base, ceid_suffix = ceid_parts[:2]

    google_info['params']['hl'] = ceid_lang_base
    if ceid_suffix and ceid_suffix not in ['Hans', 'Hant']:
        if ceid_region.lower() == ceid_lang_base:
            google_info['params']['hl'] = ceid_lang_base + '-' + ceid_region
        else:
            google_info['params']['hl'] = ceid_lang_base + '-' + ceid_suffix
    elif ceid_region.lower() != ceid_lang_base:
        if ceid_region in ['AT', 'BE', 'CH', 'IL', 'SA', 'IN', 'BD', 'PT']:
            google_info['params']['hl'] = ceid_lang_base
        else:
            google_info['params']['hl'] = ceid_lang_base + '-' + ceid_region

    google_info['params']['lr'] = 'lang_' + ceid_lang_base.split('-')[0]
    google_info['params']['gl'] = ceid_region

    query_url = (
        'https://'
        + google_info['subdomain']
        + "/search?"
        + urlencode(
            {
                'q': query,
                **google_info['params'],
            }
        )
        # ceid includes a ':' character which must not be urlencoded
        + ('&ceid=%s' % ceid)
    )
    params['url'] = query_url
    params['cookies'] = google_info['cookies']
    params['headers'].update(google_info['headers'])
    return params


def response(resp):
    """Get response from google's search request"""
    results = []
    detect_google_sorry(resp)

    # convert the text to dom
    dom = html.fromstring(resp.text)

    for result in eval_xpath_list(dom, '//div[@class="xrnccd"]'):
        # The first <a> tag in the <article> contains the link to the article.
        # The href attribute of the <a> tag is a google internal link; we have
        # to decode it.
        href = eval_xpath_getindex(result, './article/a/@href', 0)
        href = href.split('?')[0]
        href = href.split('/')[-1]
        href = base64.urlsafe_b64decode(href + '====')
        href = href[href.index(b'http'):].split(b'\xd2')[0]
        href = href.decode()

        title = extract_text(eval_xpath(result, './article/h3[1]'))

        # The pub_date is mostly a string like 'yesterday', not a real
        # timezone date or time. Therefore we can't use publishedDate.
        pub_date = extract_text(eval_xpath(result, './article//time'))
        pub_origin = extract_text(eval_xpath(result, './article//a[@data-n-tid]'))
        content = ' / '.join([x for x in [pub_origin, pub_date] if x])

        # The image URL is located in a preceding sibling <a> tag
        thumbnail = extract_text(result.xpath('preceding-sibling::a/figure/img/@src'))

        results.append(
            {
                'url': href,
                'title': title,
                'content': content,
                'thumbnail': thumbnail,
            }
        )

    # return results
    return results
