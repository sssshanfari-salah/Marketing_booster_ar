"""Smoke-check the current package layout without referencing legacy flat-module names."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import python_code.app.main as app_main
import python_code.ui.dashboard as dashboard
import python_code.config.translations as translations

print("tmp_debug OK")
print(app_main.main.__name__)
print(dashboard.__name__)
print(translations.T("Client Name"))
