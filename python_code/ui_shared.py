"""Shared window base classes and common UI entry points."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk


APP_ICON = Path(__file__).resolve().parent.parent / "starco_icon.ico"


class BaseWindow:
    """Common base for windows that share a predictable lifecycle."""

    def __init__(self, *args, title="Window", geometry="700x400", **kwargs):
        self.title_text = title
        self.geometry_size = geometry

    def configure_window(self, root):
        root.title(self.title_text)
        root.geometry(self.geometry_size)
        return root


class WelcomeWindow(tk.Tk, BaseWindow):
    """Compatibility wrapper for the canonical welcome window in clients_progress_ui."""

    def __new__(cls, *args, **kwargs):
        from clients_progress_ui import WelcomeWindow as CanonicalWelcomeWindow
        return CanonicalWelcomeWindow(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        pass


class ProgressApp(tk.Tk):
    """Compatibility wrapper for the canonical overview window in clients_progress_ui."""

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


def open_welcome_home():
    from clients_progress_ui import open_welcome_home as canonical_open_welcome_home
    return canonical_open_welcome_home()


def safe_main():
    from clients_progress_ui import safe_main as canonical_safe_main
    return canonical_safe_main()


def open_reservation_contract_form(client_name=None, client_data=None):
    from ui_reservation_contract import ShopReservationForm
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
