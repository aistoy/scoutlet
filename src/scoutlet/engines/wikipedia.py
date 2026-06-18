"""Wikipedia search engine - adapted from SearXNG.

Changes from SearXNG original:
- from searx.* → from scoutlet.*
- Removed import babel and from searx import locales, utils, network
- Removed fetch_traits() and fetch_wikimedia_traits()
- Simplified lang_map without locales.LOCALE_BEST_MATCH
- Removed TYPE_CHECKING blocks and type annotations
- Return list[dict] from response()
- Used simplified get_wiki_params with traits.get_language
"""

import logging
from urllib.parse import urlencode

from scoutlet.utils import html_to_text
from scoutlet.network import raise_for_httperror

logger = logging.getLogger("scoutlet.engines.wikipedia")

about = {
    "website": "https://www.wikipedia.org/",
    "wikidata_id": "Q52",
    "official_api_documentation": "https://en.wikipedia.org/api/rest_v1/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = []
paging = False

# Wikipedia REST API base
wikipedia_api = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
wikipedia_search = "https://{lang}.wikipedia.org/w/api.php"

# Simplified language map: locale → wiki language subdomain
lang_map = {
    "ar": "ar",
    "bg": "bg",
    "ca": "ca",
    "cs": "cs",
    "da": "da",
    "de": "de",
    "el": "el",
    "en": "en",
    "es": "es",
    "et": "et",
    "fa": "fa",
    "fi": "fi",
    "fr": "fr",
    "he": "he",
    "hr": "hr",
    "hu": "hu",
    "id": "id",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "lt": "lt",
    "lv": "lv",
    "nl": "nl",
    "no": "no",
    "pl": "pl",
    "pt": "pt",
    "ro": "ro",
    "ru": "ru",
    "sk": "sk",
    "sl": "sl",
    "sr": "sr",
    "sv": "sv",
    "th": "th",
    "tr": "tr",
    "uk": "uk",
    "vi": "vi",
    "zh": "zh",
    "zh-CN": "zh",
    "zh-HK": "zh",
    "zh-TW": "zh",
    "zh_Hans": "zh",
    "zh_Hant": "zh",
}

# Module-level traits (set via set_traits if loaded)
traits = None


def _get_wiki_language(params):
    """Determine the Wikipedia language subdomain from request params."""
    locale = params.get("searxng_locale", "en")
    if locale in lang_map:
        return lang_map[locale]
    if traits:
        lang = traits.get_language(locale, "en")
        if lang:
            return lang
    # Fallback: use first part of locale
    return locale.split("-")[0].split("_")[0]


def request(query, params):
    lang = _get_wiki_language(params)
    args = urlencode({
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "sroffset": 0,
        "srlimit": 10,
    })
    params["url"] = wikipedia_search.format(lang=lang) + "?" + args
    params["raise_for_httperror"] = True
    return params


def response(resp):
    results = []
    data = resp.json()

    lang = resp.url.host.split(".")[0] if hasattr(resp.url, "host") else "en"
    # Parse lang from URL as fallback
    if not hasattr(resp.url, "host"):
        try:
            from urllib.parse import urlparse
            parsed = urlparse(str(resp.url))
            lang = parsed.hostname.split(".")[0] if parsed.hostname else "en"
        except (ValueError, AttributeError):
            lang = "en"

    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        snippet = html_to_text(item.get("snippet", ""))

        results.append({
            "url": f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}",
            "title": title,
            "content": snippet,
        })

    return results
