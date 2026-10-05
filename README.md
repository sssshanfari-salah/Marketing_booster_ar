# Clients Manager

Desktop client-management application for tracking clients, reservations, shops, contracts, and related business workflow data.

## Project layout

The active Python package is organized under the repository root and the package directory below:

- [python_code/app/main.py](python_code/app/main.py) — application entry point
- [python_code/project_paths.py](python_code/project_paths.py) — shared path bootstrap helpers
- [python_code/ui/dashboard.py](python_code/ui/dashboard.py) — main desktop dashboard
- [python_code/ui/session.py](python_code/ui/session.py) — user/session/profile logic
- [python_code/ui/reservation_contract.py](python_code/ui/reservation_contract.py) — reservation/contract form
- [python_code/logic/clients_management.py](python_code/logic/clients_management.py) — client records and business logic
- [python_code/logic/starco_finance.py](python_code/logic/starco_finance.py) — transaction editor and reservation-status window; transaction operations delegate to FinanceManager
- [python_code/logic/finance_manager.py](python_code/logic/finance_manager.py) — contract month options, Pending transaction creation, payment-method edits, due-date updates, and validated payment status changes
- [python_code/logic/months.py](python_code/logic/months.py) — canonical contract-month generation, month indexing, previous-month lookup, and due-date coercion; client management and business logic retain compatibility imports
- [python_code/config/translations.py](python_code/config/translations.py) — language and translation logic
- [clients.json](clients.json), [users.json](users.json), [guests.json](guests.json) — runtime data files at the project root

## Run the app

From the project root, use the package entry point instead of a legacy root-level launcher:

```bash
python -m python_code.app.main
```

Open the reservation/contract form directly:

```bash
python -m python_code.app.main --reservation-form
```

## Environment setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Install the required Python packages:

```bash
pip install tkinter
pip install bidi arabic-reshaper pillow
```

If a project requirements file is added later, install from it with:

```bash
pip install -r requirements.txt
```

## Notes

- The project is a Tkinter desktop app and needs a real desktop environment for GUI startup.
- In headless environments, the app detects that condition and skips GUI startup instead of crashing.
- The canonical app entry point is the module under [python_code/app/main.py](python_code/app/main.py), not a root-level script.
- Data files are kept at the repository root and are resolved by the logic layer through the project path helpers.

## Optional packaging

The build/package flow is managed separately via [package_app.py](package_app.py) and the PyInstaller spec file [marketing_booster_ar.spec](marketing_booster_ar.spec).
