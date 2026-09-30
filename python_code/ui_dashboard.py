"""Main dashboard feature entry points.

This module is the explicit dashboard-side surface for the app, while the
reservation contract form remains in its own module for better feature separation.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

APP_ICON = Path(__file__).resolve().parent.parent / "starco_icon.ico"


class WelcomeWindow(tk.Tk):
    """Compatibility wrapper around the canonical welcome window in clients_progress_ui."""

    def __new__(cls, *args, **kwargs):
        from clients_progress_ui import WelcomeWindow as CanonicalWelcomeWindow
        return CanonicalWelcomeWindow(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        pass


class ProgressApp(tk.Tk):
    """Compatibility wrapper around the canonical dashboard app in clients_progress_ui."""

    def __new__(cls, *args, **kwargs):
        from clients_progress_ui import ProgressApp as CanonicalProgressApp
        return CanonicalProgressApp(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        pass


def build_startup_splash():
    from clients_progress_ui import build_startup_splash as canonical_build_startup_splash
    return canonical_build_startup_splash()


def open_overview_window():
    from clients_progress_ui import open_overview_window as canonical_open_overview_window
    return canonical_open_overview_window()


def open_welcome_home(force_new=False):
    from clients_progress_ui import open_welcome_home as canonical_open_welcome_home
    return canonical_open_welcome_home(force_new=force_new)


def safe_main():
    from clients_progress_ui import safe_main as canonical_safe_main
    return canonical_safe_main()


__all__ = [
    "APP_ICON",
    "ProgressApp",
    "WelcomeWindow",
    "build_startup_splash",
    "open_overview_window",
    "open_welcome_home",
    "safe_main",
]
