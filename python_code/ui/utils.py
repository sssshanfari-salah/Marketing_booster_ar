"""Compatibility layer for centralized translation helpers."""

from config.language_compat import (
    T,
    apply_bidi_text,
    configure_emoji_label,
    get_emoji_font_families,
    is_arabic_text,
    refresh_translatable_widget,
    refresh_translatable_widgets,
    set_emoji_translated_label,
)

__all__ = [
    "T",
    "apply_bidi_text",
    "configure_emoji_label",
    "get_emoji_font_families",
    "is_arabic_text",
    "refresh_translatable_widget",
    "refresh_translatable_widgets",
    "set_emoji_translated_label",
]
