"""Shared window base classes and common UI entry points."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from config.language_compat import T


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = Path(__file__).resolve().parents[1]

APP_ICON = None
for candidate in [
    PROJECT_ROOT / "starco_icon2.ico",
    PROJECT_ROOT / "starco_icon.ico",
    SOURCE_ROOT / "starco_icon2.ico",
    SOURCE_ROOT / "starco_icon.ico",
    Path(__file__).resolve().parent / "starco_icon2.ico",
    Path(__file__).resolve().parent / "starco_icon.ico",
]:
    if candidate.exists():
        APP_ICON = candidate
        break

if APP_ICON is None:
    APP_ICON = PROJECT_ROOT / "starco_icon2.ico"


class BaseWindow:
    """Common base for windows that share a predictable lifecycle."""

    def __init__(self, *args, title="Window", geometry="700x400", **kwargs):
        self.title_text = title
        self.geometry_size = geometry

    def configure_window(self, root):
        root.title(T(self.title_text) if isinstance(self.title_text, str) else self.title_text)
        root.geometry(self.geometry_size)
        return root


class WelcomeWindow(tk.Tk, BaseWindow):
    """Compatibility wrapper for the dashboard window implementation."""

    def __new__(cls, *args, **kwargs):
        try:
            from python_code.ui.dashboard import WelcomeWindow as CanonicalWelcomeWindow
        except ImportError:  # pragma: no cover - script execution fallback
            from ui.dashboard import WelcomeWindow as CanonicalWelcomeWindow
        return CanonicalWelcomeWindow(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        pass


class ProgressApp(tk.Tk):
    """Compatibility wrapper for the dashboard app implementation."""

    def __new__(cls, *args, **kwargs):
        try:
            from python_code.ui.dashboard import ProgressApp as CanonicalProgressApp
        except ImportError:  # pragma: no cover - script execution fallback
            from ui.dashboard import ProgressApp as CanonicalProgressApp
        return CanonicalProgressApp(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        pass


def build_startup_splash():
    try:
        from python_code.ui.dashboard import build_startup_splash as canonical_build_startup_splash
    except ImportError:  # pragma: no cover - script execution fallback
        from ui.dashboard import build_startup_splash as canonical_build_startup_splash
    return canonical_build_startup_splash()


def open_overview_window():
    try:
        from python_code.ui.dashboard import open_overview_window as canonical_open_overview_window
    except ImportError:  # pragma: no cover - script execution fallback
        from ui.dashboard import open_overview_window as canonical_open_overview_window
    return canonical_open_overview_window()


def open_welcome_home(force_new=False):
    try:
        from python_code.ui.dashboard import open_welcome_home as canonical_open_welcome_home
    except ImportError:  # pragma: no cover - script execution fallback
        from ui.dashboard import open_welcome_home as canonical_open_welcome_home
    return canonical_open_welcome_home(force_new=force_new)


def safe_main():
    try:
        from python_code.ui.dashboard import safe_main as canonical_safe_main
    except ImportError:  # pragma: no cover - script execution fallback
        from ui.dashboard import safe_main as canonical_safe_main
    return canonical_safe_main()


def open_reservation_contract_form(client_name=None, client_data=None):
    try:
        from python_code.ui.reservation_contract import ShopReservationForm
    except ImportError:  # pragma: no cover - script execution fallback
        from ui.reservation_contract import ShopReservationForm
    return ShopReservationForm(client_name=client_name, client_data=client_data)


__all__ = [
    "APP_ICON",
    "BaseWindow",
    "WelcomeWindow",
    "ProgressApp",
    "build_startup_splash",
    "open_overview_window",
    "open_welcome_home",
    "open_reservation_contract_form",
    "safe_main",
]
