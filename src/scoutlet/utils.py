"""Utility functions for scoutlet engines, ported from SearXNG."""

import re
import json
import types
import typing as t
from numbers import Number
from os.path import splitext, join
from random import choice
from html.parser import HTMLParser
from html import escape
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from datetime import timedelta
from pathlib import Path

from lxml import html
from lxml.etree import XPath, XPathError, XPathSyntaxError
from lxml.etree import ElementBase, _Element  # pyright: ignore[reportPrivateUsage]

from scoutlet.exceptions import SearchXPathSyntaxException, SearchEngineXPathException

import logging

logger = logging.getLogger("scoutlet.utils")

XPathSpecType: t.TypeAlias = str | XPath
ElementType: t.TypeAlias = ElementBase | _Element

_DATA_DIR = Path(__file__).parent / "data"

_BLOCKED_TAGS = ('script', 'style')

_ECMA_UNESCAPE4_RE = re.compile(r'%u([0-9a-fA-F]{4})', re.UNICODE)
_ECMA_UNESCAPE2_RE = re.compile(r'%([0-9a-fA-F]{2})', re.UNICODE)

_JS_STRING_DELIMITERS = re.compile(r'(["\'`])')
_JS_QUOTE_KEYS_RE = re.compile(r'([\{\s,])([\$_\w][\$_\w0-9]*)(:)')
_JS_VOID_OR_UNDEFINED_RE = re.compile(r'void\s+[0-9]+|void\s*\([0-9]+\)|undefined')
_JS_DECIMAL_RE = re.compile(r"([\[\,:])\s*(\-?)\s*([0-9_]*)\.([0-9_]*)")
_JS_DECIMAL2_RE = re.compile(r"([\[\,:])\s*(\-?)\s*([0-9_]+)")
_JS_EXTRA_COMA_RE = re.compile(r"\s*,\s*([\]\}])")
_JS_STRING_ESCAPE_RE = re.compile(r'\\(.)')
_JSON_PASSTHROUGH_ESCAPES = R'"\bfnrtu'

_XPATH_CACHE: dict[str, XPath] = {}


class _NotSetClass:
    pass


_NOTSET = _NotSetClass()


def _load_useragents():
    path = _DATA_DIR / "useragents.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    # Fallback user agents
    return {
        "os": ["Windows 10", "Windows 11", "Macintosh; Intel Mac OS X 10_15_7", "X11; Linux x86_64"],
        "versions": ["120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0", "124.0.0.0"],
        "ua": "Mozilla/5.0 ({os}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
    }


USER_AGENTS = _load_useragents()

# Lazy-loaded GSA user agents for Google
_gsa_useragents: list[str] | None = None


def _load_gsa_useragents() -> list[str]:
    global _gsa_useragents
    if _gsa_useragents is None:
        path = _DATA_DIR / "gsa_useragents.txt"
        if path.exists():
            with open(path) as f:
                _gsa_useragents = [line.strip() for line in f if line.strip()]
        else:
            # Fallback: use regular user agents
            _gsa_useragents = [gen_useragent()]
    return _gsa_useragents


def gen_useragent(os_string: str | None = None) -> str:
    """Return a random browser User Agent."""
    return USER_AGENTS['ua'].format(
        os=os_string or choice(USER_AGENTS['os']),
        version=choice(USER_AGENTS['versions']),
    )


def gen_gsa_useragent() -> str:
    """Return a random Google Search App User Agent (mobile Android).

    These UAs make Google return traditional HTML instead of JS-only pages.
    Loaded from data/gsa_useragents.txt (from SearXNG).
    """
    return choice(_load_gsa_useragents()) + " NSTNWV"


class HTMLTextExtractor(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.result: list[str] = []
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        if tag == 'br':
            self.result.append(' ')

    def handle_endtag(self, tag: str) -> None:
        if not self.tags:
            return
        if tag != self.tags[-1]:
            self.result.append(f"</{tag}>")
            return
        self.tags.pop()

    def is_valid_tag(self):
        return not self.tags or self.tags[-1] not in _BLOCKED_TAGS

    def handle_data(self, data: str) -> None:
        if not self.is_valid_tag():
            return
        self.result.append(data)

    def handle_charref(self, name: str) -> None:
        if not self.is_valid_tag():
            return
        if name[0] in ('x', 'X'):
            codepoint = int(name[1:], 16)
        else:
            codepoint = int(name)
        self.result.append(chr(codepoint))

    def handle_entityref(self, name: str) -> None:
        if not self.is_valid_tag():
            return
        self.result.append(name)

    def get_text(self):
        return ''.join(self.result).strip()


def html_to_text(html_str: str) -> str:
    """Extract text from a HTML string."""
    if not html_str:
        return ""
    html_str = html_str.replace('\n', ' ').replace('\r', ' ')
    html_str = ' '.join(html_str.split())
    s = HTMLTextExtractor()
    try:
        s.feed(html_str)
        s.close()
    except AssertionError:
        s = HTMLTextExtractor()
        s.feed(escape(html_str, quote=True))
        s.close()
    return s.get_text()


def extract_text(
    xpath_results: list[ElementType] | ElementType | str | Number | bool | None,
    allow_none: bool = False,
) -> str | None:
    """Extract text from a lxml result."""
    if isinstance(xpath_results, list):
        result = ''
        for e in xpath_results:
            result = result + (extract_text(e) or '')
        return result.strip()
    if isinstance(xpath_results, ElementType):
        text: str = html.tostring(
            xpath_results,
            encoding='unicode',
            method='text',
            with_tail=False,
        )
        text = text.strip().replace('\n', ' ')
        return ' '.join(text.split())
    if isinstance(xpath_results, (str, Number, bool)):
        return str(xpath_results)
    if xpath_results is None and allow_none:
        return None
    if xpath_results is None and not allow_none:
        raise ValueError('extract_text(None, allow_none=False)')
    raise ValueError('unsupported type')


def normalize_url(url: str, base_url: str) -> str:
    """Normalize URL: add protocol, join with base_url."""
    if url.startswith('//'):
        parsed_search_url = urlparse(base_url)
        url = '{0}:{1}'.format(parsed_search_url.scheme or 'http', url)
    elif url.startswith('/'):
        url = urljoin(base_url, url)
    if '://' not in url:
        url = urljoin(base_url, url)
    parsed_url = urlparse(url)
    if not parsed_url.netloc:
        raise ValueError('Cannot parse url')
    if not parsed_url.path:
        url += '/'
    return url


def extract_url(xpath_results, base_url: str) -> str:
    """Extract and normalize URL from lxml Element."""
    if xpath_results == []:
        raise ValueError('Empty url resultset')
    url = extract_text(xpath_results)
    if url:
        return normalize_url(url, base_url)
    raise ValueError('URL not found')


def extr(txt: str, begin: str, end: str, default: str = "") -> str:
    """Extract the string between begin and end from txt."""
    try:
        first = txt.index(begin) + len(begin)
        return txt[first : txt.index(end, first)]
    except ValueError:
        return default


def humanize_bytes(size: int | float, precision: int = 2):
    """Determine the human readable value of bytes."""
    s = ['B ', 'KB', 'MB', 'GB', 'TB']
    x = len(s)
    p = 0
    while size > 1024 and p < x:
        p += 1
        size = size / 1024.0
    return "%.*f %s" % (precision, size, s[p])


def humanize_number(size: int | float, precision: int = 0):
    """Determine the human readable value of a decimal number."""
    s = ['', 'K', 'M', 'B', 'T']
    x = len(s)
    p = 0
    while size > 1000 and p < x:
        p += 1
        size = size / 1000.0
    return "%.*f%s" % (precision, size, s[p])


def convert_str_to_int(number_str: str) -> int:
    """Convert number_str to int or 0."""
    if number_str.isdigit():
        return int(number_str)
    return 0


def int_or_zero(num: list[str] | str) -> int:
    if isinstance(num, list):
        if len(num) < 1:
            return 0
        num = num[0]
    return convert_str_to_int(num)


def ecma_unescape(string: str) -> str:
    """Python implementation of the unescape javascript function."""
    string = _ECMA_UNESCAPE4_RE.sub(lambda e: chr(int(e.group(1), 16)), string)
    string = _ECMA_UNESCAPE2_RE.sub(lambda e: chr(int(e.group(1), 16)), string)
    return string


def remove_pua_from_str(string: str):
    """Removes unicode PRIVATE USE CHARACTERs from a string."""
    pua_ranges = ((0xE000, 0xF8FF), (0xF0000, 0xFFFFD), (0x100000, 0x10FFFD))
    s: list[str] = []
    for c in string:
        i = ord(c)
        if any(a <= i <= b for (a, b) in pua_ranges):
            continue
        s.append(c)
    return "".join(s)


def get_xpath(xpath_spec: XPathSpecType) -> XPath:
    """Return cached compiled XPath object."""
    if isinstance(xpath_spec, str):
        result = _XPATH_CACHE.get(xpath_spec, None)
        if result is None:
            try:
                result = XPath(xpath_spec)
            except XPathSyntaxError as e:
                raise SearchXPathSyntaxException(xpath_spec, str(e.msg)) from e
            _XPATH_CACHE[xpath_spec] = result
        return result
    if isinstance(xpath_spec, XPath):
        return xpath_spec
    raise TypeError('xpath_spec must be either a str or a lxml.etree.XPath')


def eval_xpath(element: ElementType, xpath_spec: XPathSpecType) -> t.Any:
    """Equivalent of element.xpath(xpath_str) with caching."""
    xpath: XPath = get_xpath(xpath_spec)
    try:
        return xpath(element)
    except XPathError as e:
        arg = ' '.join([str(i) for i in e.args])
        raise SearchEngineXPathException(xpath_spec, arg) from e


def eval_xpath_list(element: ElementType, xpath_spec: XPathSpecType, min_len: int | None = None) -> list[t.Any]:
    """eval_xpath that ensures return is a list."""
    result: list[t.Any] = eval_xpath(element, xpath_spec)
    if not isinstance(result, list):
        raise SearchEngineXPathException(xpath_spec, 'the result is not a list')
    if min_len is not None and min_len > len(result):
        raise SearchEngineXPathException(xpath_spec, 'len(xpath_str) < ' + str(min_len))
    return result


def eval_xpath_getindex(
    element: ElementType,
    xpath_spec: XPathSpecType,
    index: int,
    default: t.Any = _NOTSET,
) -> t.Any:
    """eval_xpath_list that returns item at position index."""
    result = eval_xpath_list(element, xpath_spec)
    if -len(result) <= index < len(result):
        return result[index]
    if default == _NOTSET:
        raise SearchEngineXPathException(xpath_spec, 'index ' + str(index) + ' not found')
    return default


def get_embeded_stream_url(url: str):
    """Converts a standard video URL into its embed format."""
    parsed_url = urlparse(url)
    iframe_src = None

    if parsed_url.netloc in ['www.youtube.com', 'youtube.com'] and parsed_url.path == '/watch' and parsed_url.query:
        video_id = parse_qs(parsed_url.query).get('v', [])
        if video_id:
            iframe_src = 'https://www.youtube-nocookie.com/embed/' + video_id[0]
    elif parsed_url.netloc in ['www.facebook.com', 'facebook.com']:
        encoded_href = urlencode({'href': url})
        iframe_src = 'https://www.facebook.com/plugins/video.php?allowfullscreen=true&' + encoded_href
    elif parsed_url.netloc in ['www.instagram.com', 'instagram.com'] and parsed_url.path.startswith('/p/'):
        iframe_src = url + ('embed' if parsed_url.path.endswith('/') else '/embed')
    elif parsed_url.netloc in ['www.tiktok.com', 'tiktok.com'] and parsed_url.path.startswith('/@') and '/video/' in parsed_url.path:
        video_id = parsed_url.path.split('/video/')[1]
        iframe_src = 'https://www.tiktok.com/embed/' + video_id
    elif parsed_url.netloc in ['www.dailymotion.com', 'dailymotion.com'] and parsed_url.path.startswith('/video/'):
        path_parts = parsed_url.path.split('/')
        if len(path_parts) == 3:
            iframe_src = 'https://www.dailymotion.com/embed/video/' + path_parts[2]
    elif parsed_url.netloc in ['www.bilibili.com', 'bilibili.com'] and parsed_url.path.startswith('/video/'):
        path_parts = parsed_url.path.split('/')
        video_id = path_parts[2]
        param_key = None
        if video_id.startswith('av'):
            video_id = video_id[2:]
            param_key = 'aid'
        elif video_id.startswith('BV'):
            param_key = 'bvid'
        if param_key:
            iframe_src = f'https://player.bilibili.com/player.html?{param_key}={video_id}&high_quality=1&autoplay=false&danmaku=0'
    return iframe_src


def parse_duration_string(duration_str: str) -> timedelta | None:
    """Parse a time string in format MM:SS or HH:MM:SS."""
    duration_str = duration_str.strip()
    if not duration_str:
        return None
    try:
        time_parts = (["00"] + duration_str.split(":"))[:3]
        hours, minutes, seconds = map(int, time_parts)
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    except (ValueError, TypeError):
        pass
    return None


def load_module(filename: str, module_dir: str) -> types.ModuleType:
    """Load a Python module from file."""
    modname = splitext(filename)[0]
    modpath = join(module_dir, filename)
    spec = importlib.util.spec_from_file_location(modname, modpath)
    if not spec:
        raise ValueError(f"Error loading '{modpath}' module")
    module = importlib.util.module_from_spec(spec)
    if not spec.loader:
        raise ValueError(f"Error loading '{modpath}' module")
    spec.loader.exec_module(module)
    return module


def _j2p_process_escape(match: re.Match[str]) -> str:
    _escape = match.group(1) or match.group(2)
    return (
        Rf'\{_escape}'
        if _escape in _JSON_PASSTHROUGH_ESCAPES
        else R'\u00' if _escape == 'x' else '' if _escape == '\n' else _escape
    )


def _j2p_decimal(match: re.Match[str]) -> str:
    return (
        match.group(1)
        + match.group(2)
        + (match.group(3).replace("_", "") or "0")
        + "."
        + (match.group(4).replace("_", "") or "0")
    )


def _j2p_decimal2(match: re.Match[str]) -> str:
    return match.group(1) + match.group(2) + match.group(3).replace("_", "")


def js_obj_str_to_json_str(js_obj_str: str) -> str:
    """Convert a JS object string to JSON string."""
    if not isinstance(js_obj_str, str):
        raise ValueError("js_obj_str must be of type str")
    if js_obj_str == "":
        raise ValueError("js_obj_str can't be an empty string")

    in_string = None
    parts = _JS_STRING_DELIMITERS.split(js_obj_str)
    blackslash_just_before = False
    for i, p in enumerate(parts):
        if p == in_string and not blackslash_just_before:
            in_string = None
            parts[i] = '"'
        elif in_string:
            p = p.replace(':', chr(1))
            p = _JS_STRING_ESCAPE_RE.sub(_j2p_process_escape, p)
            if in_string == "'":
                p = p.replace('"', r'\"')
            parts[i] = p
            if blackslash_just_before and p[:1] == "'":
                parts[i - 1] = parts[i - 1][:-1]
        elif in_string is None and p in ('"', "'", "`"):
            in_string = p
            parts[i] = '"'
        elif in_string is None:
            p = _JS_VOID_OR_UNDEFINED_RE.sub("null", p)
            p = _JS_DECIMAL_RE.sub(_j2p_decimal, p)
            p = _JS_DECIMAL2_RE.sub(_j2p_decimal2, p)
            p = _JS_EXTRA_COMA_RE.sub(lambda match: match.group(1), p)
            parts[i] = p

        blackslash_just_before = len(p) > 0 and p[-1] == '\\'

    s = ''.join(parts)
    s = _JS_QUOTE_KEYS_RE.sub(r'\1"\2"\3', s)
    s = s.replace(chr(1), ':').strip()
    return s


def js_obj_str_to_python(js_obj_str: str) -> t.Any:
    """Convert a javascript variable into Python object."""
    s = js_obj_str_to_json_str(js_obj_str)
    if s == "":
        raise ValueError("js_obj_str can't be an empty string")
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        logger.debug("Internal error: js_obj_str_to_python creates invalid JSON:\n%s", s)
        raise ValueError("js_obj_str_to_python creates invalid JSON") from e


# make load_module work without top-level importlib import
import importlib
import importlib.util
