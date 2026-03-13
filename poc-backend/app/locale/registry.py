"""String registry with fallback chain: requested locale -> default locale -> key."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_strings: dict[str, dict[str, str]] = {}
_default_locale: str = "hu"


def register_locale(locale: str, strings: dict[str, str]) -> None:
    _strings[locale] = strings


def set_default_locale(locale: str) -> None:
    global _default_locale
    _default_locale = locale


def t(key: str, locale: str | None = None, **kwargs: Any) -> str:
    """Translate a key to a localized string.

    Falls back to the default locale, then to the raw key if not found.
    Supports ``str.format()`` interpolation via kwargs.
    """
    lang = locale or _default_locale
    table = _strings.get(lang) or _strings.get(_default_locale) or {}
    template = table.get(key)
    if template is None:
        logger.warning("Missing translation: key=%r locale=%r", key, lang)
        return key
    if kwargs:
        return template.format(**kwargs)
    return template
