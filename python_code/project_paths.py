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
    """Ensure the source directory is importable when running from the repo."""
    source_path = str(SOURCE_DIR)
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    return SOURCE_DIR


APP_ROOT = PROJECT_ROOT
ENTRY_SCRIPT = SOURCE_DIR / "main.py"

__all__ = [
    "APP_ROOT",
    "ENTRY_SCRIPT",
    "PROJECT_ROOT",
    "SOURCE_DIR",
    "ensure_source_on_path",
]
