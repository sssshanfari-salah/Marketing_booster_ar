"""Compatibility wrapper for the canonical dashboard application.

The project uses the implementation in ui.dashboard as the single source of truth.
This module keeps legacy imports working without duplicating the full UI logic.
"""

import tkinter as tk

try:
    from python_code.ui.dashboard import ProgressApp as CanonicalProgressApp
except ImportError:  # pragma: no cover - script execution fallback
    from ui.dashboard import ProgressApp as CanonicalProgressApp


class ProgressApp(CanonicalProgressApp):
    """Compatibility alias for the canonical dashboard app."""

    def __new__(cls, *args, **kwargs):
        return CanonicalProgressApp(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        pass


__all__ = ["ProgressApp"]
