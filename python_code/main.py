"""Application entry point for the client management desktop app.

The bootstrap is intentionally small so the runtime path setup is centralized in
project_paths.py instead of being duplicated across the project.
"""

import argparse

try:
    from .project_paths import ensure_source_on_path
except ImportError:  # pragma: no cover - script execution fallback
    from project_paths import ensure_source_on_path

ensure_source_on_path()


def launch_reservation_form():
    from ui_reservation_contract import ShopReservationForm

    form = ShopReservationForm()
    form.mainloop()
    return form


def main(argv=None):
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

    from ui_dashboard import safe_main

    safe_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())