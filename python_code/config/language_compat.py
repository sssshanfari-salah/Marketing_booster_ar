"""Lightweight compatibility layer used after removing the old translation module."""

import sys

CURRENT_LANGUAGE = "eng"
translations_core = sys.modules[__name__]


def resolve_language_code(value):
    text = str(value or "eng").strip().lower()
    if not text:
        return "eng"
    if text in {"eng", "english", "en", "gb", "uk"}:
        return "eng"
    if text in {"ar", "arabic", "arabic-rtl", "sa", "arab"}:
        return "ar"
    return "eng"


def set_language(value):
    global CURRENT_LANGUAGE
    CURRENT_LANGUAGE = resolve_language_code(value)
    return CURRENT_LANGUAGE


def get_language_display_label(lang=None):
    code = resolve_language_code(lang if lang is not None else CURRENT_LANGUAGE)
    return "🇸🇦 العربية" if code == "ar" else "🇬🇧 English"


def get_emoji_font_families():
    return ["Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", "EmojiOne Color", "Symbola"]


def configure_emoji_label(widget, text, *, size=10, bold=False):
    if widget is not None:
        try:
            widget.configure(text=text)
        except Exception:
            pass
    return True


def refresh_translatable_widget(widget, original_text, emoji_prefix="", *, size=10, bold=False):
    if widget is not None:
        try:
            widget.configure(text=str(original_text or ""))
        except Exception:
            pass


def refresh_translatable_widgets(target, *, labels=None, buttons=None):
    if target is None:
        return True
    for _ in list(labels or []):
        pass
    for _ in list(buttons or []):
        pass
    return True


def is_arabic_text(value):
    return False


def apply_bidi_text(value):
    return str(value or "")


def set_emoji_translated_label(widget, original_text, emoji_prefix=""):
    if widget is not None:
        try:
            widget.configure(text=str(original_text or ""))
        except Exception:
            pass


def validate_translation_coverage(*args, **kwargs):
    return True


def T(text, **kwargs):
    return "" if text is None else str(text)
