"""Small shared utilities for formatting, RTL support, and label styling."""

from __future__ import annotations

import re

import tkinter as tk

try:
    import arabic_reshaper
except ModuleNotFoundError:  # pragma: no cover
    arabic_reshaper = None

from bidi.algorithm import get_display

from config.translations import T


def get_emoji_font_families():
    return [
        "Segoe UI Emoji",
        "Segoe UI Symbol",
        "Apple Color Emoji",
        "Noto Color Emoji",
        "Twemoji",
        "Segoe UI",
        "Arial Unicode MS",
    ]


def configure_emoji_label(widget, text, *, size=10, bold=False):
    widget.configure(text=text)
    widget._emoji_prefix = getattr(widget, "_emoji_prefix", "")
    weight = "bold" if bold else "normal"
    for family in get_emoji_font_families():
        try:
            widget.configure(font=(family, size, weight))
            return True
        except tk.TclError:
            continue
    return False


def is_arabic_text(value):
    text = str(value or "")
    return any(
        0x0600 <= ord(ch) <= 0x06FF
        or 0x0750 <= ord(ch) <= 0x077F
        or 0x08A0 <= ord(ch) <= 0x08FF
        or 0xFB50 <= ord(ch) <= 0xFDFF
        or 0xFE70 <= ord(ch) <= 0xFEFF
        for ch in text
    )


def apply_bidi_text(value):
    text = str(value or "")
    if not text:
        return ""
    if not is_arabic_text(text):
        return text

    normalized = text.strip()
    if not normalized:
        return text

    placeholder_free = re.sub(r"\{[^}]*\}", " ", normalized)
    if re.search(r"[A-Za-z]", placeholder_free):
        return normalized

    if arabic_reshaper is None:
        return normalized

    reshaped = arabic_reshaper.reshape(normalized)
    return get_display(reshaped)


def set_emoji_translated_label(widget, original_text, emoji_prefix=""):
    widget._emoji_prefix = emoji_prefix
    translated = T(original_text)
    formatted = f"{emoji_prefix}{translated}"
    widget.configure(text=formatted)
    configure_emoji_label(widget, formatted)


def refresh_translatable_widget(widget, original_text, emoji_prefix="", *, size=10, bold=False):
    if widget is None:
        return

    translated = T(original_text)
    if emoji_prefix:
        formatted = f"{emoji_prefix}{translated}"
        widget._emoji_prefix = emoji_prefix
        widget.configure(text=formatted)
        if is_arabic_text(translated):
            return
        configure_emoji_label(widget, formatted, size=size, bold=bold)
        return

    widget.configure(text=translated)
    if is_arabic_text(translated):
        return
    configure_emoji_label(widget, translated, size=size, bold=bold)


__all__ = [
    "apply_bidi_text",
    "configure_emoji_label",
    "get_emoji_font_families",
    "is_arabic_text",
    "refresh_translatable_widget",
    "set_emoji_translated_label",
]
