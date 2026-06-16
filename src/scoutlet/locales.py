"""Locale utilities for scoutlet, ported from SearXNG's locales.py."""

from __future__ import annotations

import typing as t

import babel
import babel.core
import babel.languages

import logging

log = logging.getLogger("scoutlet.locales")


def region_tag(locale: babel.Locale) -> str:
    """Returns region tag from the locale (e.g. zh-TW, en-US)."""
    if not locale.territory:
        raise ValueError('babel.Locale %s: missed a territory' % locale)
    return locale.language + '-' + locale.territory


def language_tag(locale: babel.Locale) -> str:
    """Returns language tag from the locale (e.g. en, zh_Hant)."""
    sxng_lang = locale.language
    if locale.script:
        sxng_lang += '_' + locale.script
    return sxng_lang


def get_locale(locale_tag: str) -> babel.Locale | None:
    """Parse a locale tag into a babel Locale."""
    try:
        return babel.Locale.parse(locale_tag, sep='-')
    except babel.core.UnknownLocaleError:
        return None


def get_official_locales(
    territory: str, languages: list[str] | None = None, regional: bool = False, de_facto: bool = True
) -> set[babel.Locale]:
    """Returns official locales for a territory."""
    ret_val: set[babel.Locale] = set()
    o_languages = babel.languages.get_official_languages(territory, regional=regional, de_facto=de_facto)
    if languages:
        languages = [l.lower() for l in languages]
        o_languages = set(l for l in o_languages if l.lower() in languages)
    for lang in o_languages:
        try:
            locale = babel.Locale.parse(lang + '_' + territory)
            ret_val.add(locale)
        except babel.UnknownLocaleError:
            continue
    return ret_val


def get_engine_locale(searxng_locale: str, engine_locales: dict[str, str], default: str | None = None) -> str | None:
    """Return engine's locale string that best fits to searxng_locale.

    Ported from SearXNG's get_engine_locale with the same matching logic:
    1. Direct 1:1 mapping
    2. Narrow by territory (official languages)
    3. Narrow by language (population percent)
    """
    # Direct mapping
    engine_locale = engine_locales.get(searxng_locale)
    if engine_locale is not None:
        return engine_locale

    try:
        locale = babel.Locale.parse(searxng_locale, sep='-')
    except babel.core.UnknownLocaleError:
        try:
            locale = babel.Locale.parse(searxng_locale.split('-')[0])
        except babel.core.UnknownLocaleError:
            return default

    # Try language tag (e.g. zh_Hant)
    searxng_lang = language_tag(locale)
    engine_locale = engine_locales.get(searxng_lang)
    if engine_locale is not None:
        return engine_locale

    # Narrow by territory
    if locale.territory:
        for official_language in babel.languages.get_official_languages(locale.territory, de_facto=True):
            searxng_locale = official_language + '-' + locale.territory
            engine_locale = engine_locales.get(searxng_locale)
            if engine_locale is not None:
                return engine_locale

    # Narrow by language across territories
    if locale.language:
        terr_lang_dict: dict[str, dict[str, t.Any]] = {}
        for territory, langs in babel.core.get_global("territory_languages").items():
            _lang = langs.get(searxng_lang)
            if _lang is None or _lang.get('official_status') is None:
                continue
            terr_lang_dict[territory] = _lang

        territory = locale.language.upper()
        if territory == 'EN':
            territory = 'US'

        if terr_lang_dict.get(territory):
            searxng_locale = locale.language + '-' + territory
            engine_locale = engine_locales.get(searxng_locale)
            if engine_locale is not None:
                return engine_locale

        terr_lang_list = sorted(terr_lang_dict.items(), key=lambda item: item[1]['population_percent'], reverse=True)
        for territory, _lang in terr_lang_list:
            searxng_locale = locale.language + '-' + territory
            engine_locale = engine_locales.get(searxng_locale)
            if engine_locale is not None:
                return engine_locale

    if engine_locale is None:
        engine_locale = default

    return engine_locale
