"""Application package for the client management desktop app.

This file marks the source directory as a package and keeps the project import
structure predictable for future maintenance work.
"""

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

from . import project_paths

__all__ = [
    "project_paths",
]
