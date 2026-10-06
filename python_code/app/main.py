"""Application entry point for the client management desktop app.

The bootstrap is intentionally small so the runtime path setup is centralized in
project_paths.py instead of being duplicated across the project.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path(__file__).resolve().parents[1]

if getattr(sys, "frozen", False):
    bundled_root = Path(sys._MEIPASS)
    for candidate in (bundled_root, bundled_root / "python_code"):
        candidate_str = str(candidate)
        if candidate.exists() and candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)

for candidate in (str(PROJECT_ROOT), str(SOURCE_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

try:
    from python_code.project_paths import ensure_source_on_path
except ImportError:  # pragma: no cover - direct script fallback
    from project_paths import ensure_source_on_path

ensure_source_on_path()


def launch_reservation_form():
    try:
        from python_code.ui.reservation_contract import ShopReservationForm
    except ImportError:  # pragma: no cover - script fallback
        from ui.reservation_contract import ShopReservationForm

    form = ShopReservationForm()
    form.mainloop()
    return form


def main(argv=None):
    try:
        from logic.validations.Storage.client_storage import migrate_legacy_client_files
    except ImportError:  # pragma: no cover - package import fallback
        from python_code.logic.validations.Storage.client_storage import migrate_legacy_client_files

    migrate_legacy_client_files(PROJECT_ROOT)

    parser = argparse.ArgumentParser(description="Starco Client Manager")
    parser.add_argument(
        "--reservation-form",
        "--contract-form",
        action="store_true",
        dest="reservation_form",
        help="Open the reservation contract form instead of the main dashboard.",
    )
    args = parser.parse_args(argv)

    if args.reservation_form:
        launch_reservation_form()
        return 0

    try:
        from python_code.ui.dashboard import safe_main
    except ImportError:  # pragma: no cover - script fallback
        from ui.dashboard import safe_main

    safe_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())