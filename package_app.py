import calendar
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
SOURCE_DIR = APP_DIR / "python code"
ENTRY_SCRIPT = SOURCE_DIR / "main.py"
DIST_DIR = APP_DIR / "dist"
BUILD_DIR = APP_DIR / "build"
APP_NAME = "marketing_booster_ar"
APP_DISPLAY_NAME = "Clients Manager"
DEFAULT_COUNTRY_CODE = "+968"
SPEC_FILE = APP_DIR / f"{APP_NAME}.spec"


def resolve_target_icon():
    candidates = [
        APP_DIR / "starco_icon.ico",
        APP_DIR / "starco icon" / "starco_icon.ico",
        APP_DIR / "starco icon" / "icon.ico",
        APP_DIR / "starco icon" / "app_icon.ico",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return APP_DIR / "starco_icon.ico"


TARGET_ICON = resolve_target_icon()
COUNTRY_CODES_DATA = SOURCE_DIR / "country_codes.json"
SHOPS_ELECTRICAL_METERS_FILE = SOURCE_DIR / "Shops_Elect_meters.json"
CLIENTS_DATA_FILE = APP_DIR / "clients.json"
LEGACY_CLIENTS_DATA_FILE = SOURCE_DIR / "clients.json"
DOCUMENTS_DATA_FILE = SOURCE_DIR / "docs" / "documents.txt"
SUPPORTING_DOCUMENTS_DIR = APP_DIR / "supporting_documents"
STARCO_RENT_CONTRACT = SUPPORTING_DOCUMENTS_DIR / "starco_rent_contract_1.pdf"
APPLICATION_OUTPUTS_DIR = APP_DIR / "application_outputs"
CLIENTS_ROOT_DIR = APP_DIR / "Clients"
CLIENT_LOGS_DIR = APPLICATION_OUTPUTS_DIR / "clients_logs"
TASK_LOGS_DIR = APPLICATION_OUTPUTS_DIR / "tasks_logs"
OBSERVATION_LOGS_DIR = APPLICATION_OUTPUTS_DIR / "observation_logs"
OUTPUT_LOG_DIRS = [APPLICATION_OUTPUTS_DIR, CLIENT_LOGS_DIR, TASK_LOGS_DIR, OBSERVATION_LOGS_DIR]
PROJECT_RUNTIME_DIRECTORIES = [
    APP_DIR / "supporting_documents",
    APP_DIR / "starco icon",
    SOURCE_DIR,
    SOURCE_DIR / "docs",
    CLIENTS_ROOT_DIR,
    *OUTPUT_LOG_DIRS,
]
REQUIRED_RUNTIME_DIRECTORIES = list(PROJECT_RUNTIME_DIRECTORIES)
LEGACY_APP_NAMES = ["marketing_booster", "marketing_booster_ar"]
LEGACY_DISPLAY_NAMES = ["Marketing Booster", "Marketing Booster AR", "Clients Manager", "Starco Commercial Complex"]
RUNTIME_DATA_FILES = [
    TARGET_ICON,
    CLIENTS_DATA_FILE,
    COUNTRY_CODES_DATA,
    SHOPS_ELECTRICAL_METERS_FILE,
    DOCUMENTS_DATA_FILE,
    STARCO_RENT_CONTRACT,
    *PROJECT_RUNTIME_DIRECTORIES,
]

# Keep the packaged app aligned with the current client-manager UI/data model.
RUNTIME_DATA_FILES = [path for path in RUNTIME_DATA_FILES if path is not None and path.exists()]


def validate_runtime_asset_catalog():
    required_paths = [
        ENTRY_SCRIPT,
        SOURCE_DIR / "main.py",
        SOURCE_DIR / "clients_management.py",
        SOURCE_DIR / "clients_progress_ui.py",
        CLIENTS_DATA_FILE,
        LEGACY_CLIENTS_DATA_FILE,
        COUNTRY_CODES_DATA,
        SHOPS_ELECTRICAL_METERS_FILE,
        DOCUMENTS_DATA_FILE,
        SUPPORTING_DOCUMENTS_DIR,
        *REQUIRED_RUNTIME_DIRECTORIES,
    ]

    missing_paths = [str(path) for path in required_paths if path is not None and not path.exists()]
    if missing_paths:
        details = "\n".join(f" - {missing}" for missing in missing_paths)
        raise FileNotFoundError(
            "Packaging aborted: required runtime folders/files are missing.\n"
            f"{details}"
        )

    ui_file = SOURCE_DIR / "clients_progress_ui.py"
    ui_markers = [
        "Project Manager To-Do",
        "generate_project_manager_todo_tasks",
        "load_shop_electrical_meter_map",
        "self.client_selector_var",
        "_switch_client_for_transactions",
        "ClientTransactionsWindow",
        "open_welcome_home",
        "No reviews yet",
        "self.transactions_button",
        "Home",
        "go_home",
    ]
    ui_content = ui_file.read_text(encoding="utf-8") if ui_file.exists() else ""
    missing_markers = [marker for marker in ui_markers if marker not in ui_content]
    if missing_markers:
        details = "\n".join(f" - {marker}" for marker in missing_markers)
        raise RuntimeError(
            "Packaging aborted: the app UI is out of sync with the latest project-management and transaction workflow.\n"
            f"Missing markers:\n{details}"
        )

    # Keep packaging aligned with the latest client-manager/export/report workflow.
    for directory in PROJECT_RUNTIME_DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)

    return True


def collect_runtime_assets():
    assets = []
    seen = set()
    for path in RUNTIME_DATA_FILES:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        assets.append(path)
    return assets


def generate_contract_months(start_date=None, end_date=None):
    start_value = str(start_date or "").strip()
    end_value = str(end_date or "").strip()
    if not start_value and not end_value:
        return []

    def parse_date(value):
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    start_dt = parse_date(start_value)
    end_dt = parse_date(end_value)

    if start_dt is None and end_dt is not None:
        start_dt = end_dt.replace(day=1)
    if end_dt is None and start_dt is not None:
        end_dt = start_dt.replace(day=28)
    if start_dt is None or end_dt is None:
        return []

    if end_dt < start_dt:
        start_dt, end_dt = end_dt, start_dt

    months = []
    current = start_dt.replace(day=1)
    while current <= end_dt:
        months.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    seen = set()
    unique_months = []
    for month in months:
        if month in seen:
            continue
        seen.add(month)
        unique_months.append(month)
    return unique_months


def normalize_contract_details(value):
    contract_fields = {
        "contract_number": "",
        "starting_date": "",
        "ending_date": "",
        "commercial_registration_number": "",
        "authorized_signature_name": "",
        "rent_value": "",
        "currency_type": "OMR",
        "open_issues": "",
    }

    if not isinstance(value, dict):
        return dict(contract_fields)

    normalized = {}
    for key, default in contract_fields.items():
        raw = value.get(key, default)
        normalized[key] = str(raw) if raw is not None else default
    return normalized


def normalize_payment_method(value):
    choices = ["Cash", "Cheque", "Bank Transaction"]
    if value is None:
        return "Cash"

    normalized = str(value).strip()
    if not normalized:
        return "Cash"

    lookup = {choice.lower(): choice for choice in choices}
    if normalized.lower() in lookup:
        return lookup[normalized.lower()]

    for choice in choices:
        if normalized.lower() in choice.lower():
            return choice

    return "Cash"


def coerce_due_date_for_month(month_value, due_date_value):
    month_text = str(month_value or "").strip()
    if not month_text:
        return str(due_date_value or "").strip()

    try:
        month_start = datetime.strptime(f"{month_text}-01", "%Y-%m-%d")
    except ValueError:
        return str(due_date_value or "").strip()

    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    month_end = datetime(month_start.year, month_start.month, last_day).strftime("%Y-%m-%d")

    value = str(due_date_value or "").strip()
    if not value:
        return month_end

    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return month_end

    if parsed.year == month_start.year and parsed.month == month_start.month:
        return parsed.strftime("%Y-%m-%d")
    return month_end


def is_transaction_complete(value):
    if not isinstance(value, dict):
        return False

    month = str(value.get("month", "") or "").strip()
    amount = str(value.get("amount", "") or "").strip()
    due_date = str(value.get("due_date", "") or "").strip()
    payment_method = normalize_payment_method(value.get("payment_method", "Cash"))
    cheque_number = str(value.get("cheque_number", "") or "").strip()
    bank_transaction_details = str(value.get("bank_transaction_details", "") or "").strip()

    if not month or not amount or not due_date:
        return False

    if payment_method == "Cheque":
        return bool(cheque_number)
    if payment_method == "Bank Transaction":
        return bool(bank_transaction_details)
    return True


def normalize_transaction_entry(value):
    transaction_fields = {
        "month": "",
        "status": "",
        "amount": "",
        "payment_method": "Cash",
        "cheque_number": "",
        "due_date": "",
        "bank_name": "",
        "bank_transaction_details": "",
    }

    if not isinstance(value, dict):
        return dict(transaction_fields)

    normalized = {}
    for key, default in transaction_fields.items():
        raw = value.get(key, default)
        if key == "payment_method":
            normalized[key] = normalize_payment_method(raw)
        elif key == "status":
            normalized[key] = str(raw) if raw is not None else default
        else:
            normalized[key] = str(raw) if raw is not None else default

    normalized["due_date"] = coerce_due_date_for_month(normalized.get("month", ""), normalized.get("due_date", ""))

    raw_status = str(normalized.get("status", "") or "").strip().lower()
    if raw_status in {"paid", "completed", "complete", "success", "successful", "yes", "true", "1"} and is_transaction_complete(normalized):
        normalized["status"] = "Paid"
    else:
        normalized["status"] = "Pending"

    if normalized["payment_method"] == "Cheque":
        normalized["cheque_number"] = str(normalized.get("cheque_number", "") or "").strip()
    else:
        normalized["cheque_number"] = ""

    if normalized["payment_method"] == "Bank Transaction":
        normalized["bank_transaction_details"] = str(normalized.get("bank_transaction_details", "") or "").strip()
    else:
        normalized["bank_transaction_details"] = ""

    return normalized


def build_project_manager_todo_tasks(clients):
    tasks = []
    for client in clients or []:
        if not isinstance(client, dict):
            continue

        name = str(client.get("name") or client.get("Client Name") or "Client").strip() or "Client"
        contract_details = client.get("contract_details") or {}
        if not isinstance(contract_details, dict):
            contract_details = {}
        start_date = str(contract_details.get("starting_date") or "").strip()
        end_date = str(contract_details.get("ending_date") or "").strip()
        months = generate_contract_months(start_date, end_date)
        if not months:
            continue

        transactions = client.get("transactions") or []
        if not isinstance(transactions, list):
            transactions = []

        transactions_by_month = {}
        for entry in transactions:
            if not isinstance(entry, dict):
                continue
            month = str(entry.get("month", "") or "").strip()
            if month:
                transactions_by_month[month] = entry

        for month in months:
            entry = transactions_by_month.get(month)
            status = str((entry or {}).get("status", "") or "").strip().lower()
            if entry is not None and status in {"paid", "completed", "complete", "success", "successful"}:
                continue
            tasks.append(f"Follow up payment for {name} - {month}")

    return tasks if tasks else ["No pending payment follow-ups"]


def normalize_legacy_client_data(entries):
    normalized = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue

        normalized_entry = dict(entry)

        contract_details = normalized_entry.get("contract_details")
        if not isinstance(contract_details, dict):
            contract_details = {}
        else:
            contract_details = dict(contract_details)
        normalized_entry["contract_details"] = normalize_contract_details(contract_details)
        normalized_entry["contract_details"].setdefault("currency_type", "OMR")

        progress_data = normalized_entry.get("progress")
        if not isinstance(progress_data, dict):
            progress_data = {}
        normalized_entry["progress"] = dict(progress_data)

        reviews = normalized_entry.get("reviews")
        if not isinstance(reviews, list):
            reviews = []
        normalized_entry["reviews"] = list(reviews)

        transactions = normalized_entry.get("transactions")
        if not isinstance(transactions, list):
            transactions = []

        normalized_transactions = []
        for item in transactions:
            transaction = normalize_transaction_entry(item)
            transaction["payment_method"] = normalize_payment_method(transaction.get("payment_method", "Cash"))
            transaction["bank_name"] = str(transaction.get("bank_name", "") or "").strip()
            transaction["cheque_number"] = str(transaction.get("cheque_number", "") or "").strip()
            transaction["bank_transaction_details"] = str(transaction.get("bank_transaction_details", "") or "").strip()
            normalized_transactions.append(transaction)

        normalized_entry["transactions"] = normalized_transactions
        normalized.append(normalized_entry)

    return normalized


def migrate_legacy_client_data():
    if CLIENTS_DATA_FILE.exists() and not LEGACY_CLIENTS_DATA_FILE.exists():
        return

    if not LEGACY_CLIENTS_DATA_FILE.exists():
        if not CLIENTS_DATA_FILE.exists():
            CLIENTS_DATA_FILE.write_text("[]", encoding="utf-8")
        else:
            try:
                canonical_data = json.loads(CLIENTS_DATA_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError, TypeError):
                canonical_data = []
            if not isinstance(canonical_data, list):
                canonical_data = []
            CLIENTS_DATA_FILE.write_text(json.dumps(normalize_legacy_client_data(canonical_data), indent=2), encoding="utf-8")
        return

    try:
        legacy_data = json.loads(LEGACY_CLIENTS_DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError):
        legacy_data = []

    if not isinstance(legacy_data, list):
        legacy_data = []

    if CLIENTS_DATA_FILE.exists():
        try:
            canonical_data = json.loads(CLIENTS_DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, TypeError):
            canonical_data = []
    else:
        canonical_data = []

    if not isinstance(canonical_data, list):
        canonical_data = []

    seen = set()
    merged = []
    for entry in normalize_legacy_client_data(canonical_data + legacy_data):
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or entry.get("Client Name") or "").strip().lower()
        contact = str(entry.get("contact") or entry.get("Contact") or "").strip()
        key = (name, contact)
        if not key[0] and not key[1]:
            continue
        if key in seen:
            continue
        seen.add(key)
        merged.append(entry)

    CLIENTS_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    CLIENTS_DATA_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")


def add_runtime_assets(cmd):
    for path in collect_runtime_assets():
        if not path.exists():
            continue
        if path.is_dir():
            cmd.extend(["--add-data", f"{path}{os.pathsep}."])
        else:
            cmd.extend(["--add-data", f"{path}{os.pathsep}."])
    return cmd


def resolve_desktop_dir():
    home = Path.home()
    candidate_paths = [
        home / "Desktop",
        home / "OneDrive" / "Desktop",
        home / "OneDrive - Personal" / "Desktop",
        home / "OneDrive - Business" / "Desktop",
    ]

    for candidate in candidate_paths:
        resolved = candidate.resolve(strict=False)
        if resolved.exists():
            return resolved

    return (home / "Desktop").resolve(strict=False)


DESKTOP_DIR = resolve_desktop_dir()


def remove_stale_artifacts():
    for legacy_name in LEGACY_APP_NAMES:
        stale_paths = [
            DIST_DIR / f"{legacy_name}.exe",
            DIST_DIR / legacy_name / f"{legacy_name}.exe",
            DIST_DIR / f"{legacy_name}.app",
        ]
        for stale in stale_paths:
            if stale.exists():
                if stale.is_dir():
                    try:
                        for child in stale.iterdir():
                            child.unlink()
                    except OSError:
                        pass
                    try:
                        stale.rmdir()
                    except OSError:
                        pass
                else:
                    try:
                        stale.unlink()
                    except OSError:
                        pass

    for legacy_name in LEGACY_DISPLAY_NAMES:
        desktop_link = DESKTOP_DIR / f"{legacy_name}.lnk"
        if desktop_link.exists():
            try:
                desktop_link.unlink()
            except OSError:
                pass

    desktop_link = DESKTOP_DIR / f"{APP_DISPLAY_NAME}.lnk"
    if desktop_link.exists():
        try:
            desktop_link.unlink()
        except OSError:
            pass


def find_built_exe():
    candidates = [
        DIST_DIR / f"{APP_NAME}.exe",
        DIST_DIR / APP_NAME / f"{APP_NAME}.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


TARGET_EXE = find_built_exe()


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
        return True
    except ModuleNotFoundError:
        return False


def ensure_pywin32():
    try:
        import win32com.client  # noqa: F401
        return True
    except ModuleNotFoundError:
        return False


def force_remove_path(path, retries=8, delay=0.5):
    if not path.exists():
        return

    for attempt in range(retries):
        try:
            if path.is_dir() and not path.is_symlink():
                for root, dirs, files in os.walk(path, topdown=False):
                    for name in files:
                        file_path = Path(root) / name
                        try:
                            file_path.unlink()
                        except PermissionError:
                            os.chmod(file_path, 0o777)
                            file_path.unlink()
                    for name in dirs:
                        dir_path = Path(root) / name
                        try:
                            dir_path.rmdir()
                        except OSError:
                            os.chmod(dir_path, 0o777)
                            dir_path.rmdir()
                path.rmdir()
            else:
                path.unlink()
            return
        except (PermissionError, OSError):
            if attempt == retries - 1:
                raise
            os.chmod(path, 0o777)
            if path.is_dir():
                for child in path.iterdir():
                    try:
                        os.chmod(child, 0o777)
                    except OSError:
                        pass
            time.sleep(delay)


def remove_directory(path):
    if not path.exists():
        return

    try:
        force_remove_path(path)
    except (PermissionError, OSError):
        print(f"Warning: could not fully remove {path}. Continuing with the rebuild attempt.")


def ensure_runtime_files():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    for output_dir in OUTPUT_LOG_DIRS:
        output_dir.mkdir(parents=True, exist_ok=True)

    if not ENTRY_SCRIPT.exists():
        raise FileNotFoundError(f"Entry script not found: {ENTRY_SCRIPT}")

    migrate_legacy_client_data()

    if not CLIENTS_DATA_FILE.exists():
        CLIENTS_DATA_FILE.write_text("[]", encoding="utf-8")

    CLIENTS_ROOT_DIR.mkdir(parents=True, exist_ok=True)

    COUNTRY_CODES_DATA.parent.mkdir(parents=True, exist_ok=True)
    if not COUNTRY_CODES_DATA.exists():
        COUNTRY_CODES_DATA.write_text("[]", encoding="utf-8")

    SHOPS_ELECTRICAL_METERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SHOPS_ELECTRICAL_METERS_FILE.exists():
        SHOPS_ELECTRICAL_METERS_FILE.write_text("[]", encoding="utf-8")

    DOCUMENTS_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DOCUMENTS_DATA_FILE.exists():
        DOCUMENTS_DATA_FILE.write_text("", encoding="utf-8")

    SUPPORTING_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    if STARCO_RENT_CONTRACT.exists() and not STARCO_RENT_CONTRACT.is_file():
        raise ValueError(f"Expected a file at: {STARCO_RENT_CONTRACT}")

    if not TARGET_ICON.exists():
        fallback_icon_dir = APP_DIR / "starco icon"
        if fallback_icon_dir.exists():
            for candidate in sorted(fallback_icon_dir.iterdir()):
                if candidate.suffix.lower() in {".ico", ".png", ".jpg", ".jpeg"}:
                    try:
                        shutil.copy2(candidate, TARGET_ICON)
                        break
                    except OSError:
                        pass

    if not TARGET_ICON.exists() and (APP_DIR / "starco icon").exists():
        for candidate in sorted((APP_DIR / "starco icon").iterdir()):
            if candidate.suffix.lower() in {".ico", ".png", ".jpg", ".jpeg"}:
                try:
                    shutil.copy2(candidate, TARGET_ICON)
                    break
                except OSError:
                    pass


def build_app():
    ensure_runtime_files()
    validate_runtime_asset_catalog()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    remove_stale_artifacts()
    remove_directory(BUILD_DIR)
    remove_directory(DIST_DIR)

    if not ensure_pyinstaller():
        print("PyInstaller is not installed. Installing it now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    if SPEC_FILE.exists():
        SPEC_FILE.unlink()

    if not ENTRY_SCRIPT.exists():
        raise FileNotFoundError(f"Entry script missing: {ENTRY_SCRIPT}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(APP_DIR),
    ]

    if TARGET_ICON.exists():
        cmd.extend(["--icon", str(TARGET_ICON)])

    cmd = add_runtime_assets(cmd)

    cmd.append(str(ENTRY_SCRIPT))

    print("Building app...")
    subprocess.check_call(cmd, cwd=str(APP_DIR))

    return find_built_exe()


def create_shortcut():
    exe_path = find_built_exe()
    if exe_path is None or not exe_path.exists():
        print("Executable not found. Build the app first.")
        return None

    if not ensure_pywin32():
        print("pywin32 is required to create the desktop shortcut. Install it with:")
        print("python -m pip install pywin32")
        return None

    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    desktop_link = DESKTOP_DIR / f"{APP_DISPLAY_NAME}.lnk"

    try:
        import win32com.client as win32com_client
    except ImportError:
        print("pywin32 is required to create the desktop shortcut. Install it with:")
        print("python -m pip install pywin32")
        return None

    shell = win32com_client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(desktop_link))
    shortcut.Targetpath = str(exe_path)
    shortcut.WorkingDirectory = str(exe_path.parent)
    shortcut.IconLocation = str(TARGET_ICON if TARGET_ICON.exists() else exe_path)
    shortcut.WindowStyle = 7
    shortcut.Arguments = ""
    shortcut.save()

    print(f"Shortcut created: {desktop_link}")
    return desktop_link


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("This packaging script is for Windows only.")

    exe = build_app()
    if exe is None:
        raise SystemExit("App build failed.")

    print(f"Built: {exe}")
    shortcut = create_shortcut()
    if shortcut is not None:
        print(f"Desktop shortcut: {shortcut}")
