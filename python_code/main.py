# Application entry point.
# This file prepares the runtime path and starts the user interface for the client manager.
import argparse
import sys
from pathlib import Path

# Ensure the source folder is importable when the app is launched from its project directory.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


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

    from clients_progress_ui import safe_main

    safe_main()
    return 0


# Launch the main UI when the script is executed directly.
if __name__ == "__main__":
    raise SystemExit(main())