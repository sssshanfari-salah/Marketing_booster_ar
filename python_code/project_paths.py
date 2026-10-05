"""Shared project path helpers used throughout the app.

Centralizing these paths avoids duplicate `sys.path` manipulation and keeps the
application bootstrap consistent as the codebase grows.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = Path(__file__).resolve().parent


def ensure_source_on_path() -> Path:
    """Ensure the project source tree is importable from any repo entry point."""
    for candidate in (SOURCE_DIR, PROJECT_ROOT):
        path_value = str(candidate)
        if path_value not in sys.path:
            sys.path.insert(0, path_value)
    return SOURCE_DIR


APP_ROOT = PROJECT_ROOT
ENTRY_SCRIPT = SOURCE_DIR / "app" / "main.py"

__all__ = [
    "APP_ROOT",
    "ENTRY_SCRIPT",
    "PROJECT_ROOT",
    "SOURCE_DIR",
    "ensure_source_on_path",
]
