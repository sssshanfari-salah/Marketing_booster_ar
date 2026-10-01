"""Verify the current translation layer without using retired flat-module paths."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python_code.config import translations as translations

translations.set_language("ar")
label = "Client Name"
result = translations.T(label)
assert isinstance(result, str)
print("verify_language_fix OK")
print(result.encode("unicode_escape").decode("ascii"))
