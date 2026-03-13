"""Localization layer for user-facing strings.

Usage::

    from app.locale import t

    msg = t("bot.processing")          # uses default locale from settings
    msg = t("bot.processing", "en")    # explicit locale override
"""

from app.locale.registry import t

__all__ = ["t"]
