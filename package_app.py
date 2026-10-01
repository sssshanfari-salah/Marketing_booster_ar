import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def resolve_source_dir():
    return APP_DIR / "python_code"


SOURCE_DIR = resolve_source_dir()
ENTRY_SCRIPT = SOURCE_DIR / "app" / "main.py"
DIST_DIR = APP_DIR / "dist"
BUILD_DIR = APP_DIR / "build"
APP_NAME = "marketing_booster_ar"


def build_default_shop_meter_catalog():
    return [
        {"Shop": "1", "Elec meter": "28600022"},
        {"Shop": "2", "Elec meter": "28602713"},
        {"Shop": "3", "Elec meter": "28602714"},
        {"Shop": "4", "Elec meter": "28602710"},
        {"Shop": "5", "Elec meter": "28602692"},
        {"Shop": "6", "Elec meter": "28602712"},
        {"Shop": "7", "Elec meter": "28602709"},
        {"Shop": "8", "Elec meter": "28602711"},
        {"Shop": "9", "Elec meter": "28609691"},
        {"Shop": "10", "Elec meter": "28609681"},
        {"Shop": "11", "Elec meter": "28609682"},
        {"Shop": "12", "Elec meter": "28609687"},
        {"Shop": "13", "Elec meter": "28609683"},
        {"Shop": "14", "Elec meter": "28609688"},
        {"Shop": "15", "Elec meter": "28609689"},
        {"Shop": "16", "Elec meter": "28609684"},
        {"Shop": "17", "Elec meter": "28609685"},
        {"Shop": "18", "Elec meter": "28609690"},
        {"Shop": "19", "Elec meter": "28609692"},
        {"Shop": "20", "Elec meter": "28609693"},
        {"Shop": "21", "Elec meter": "28609694"},
        {"Shop": "22", "Elec meter": "28609695"},
        {"Shop": "23", "Elec meter": "28609696"},
        {"Shop": "24", "Elec meter": "28609697"},
        {"Shop": "25", "Elec meter": "28609698"},
        {"Shop": "26", "Elec meter": "28609699"},
        {"Shop": "27", "Elec meter": "28609700"},
        {"Shop": "28", "Elec meter": "28609701"},
        {"Shop": "29", "Elec meter": "28609702"},
        {"Shop": "30", "Elec meter": "28609703"},
        {"Shop": "31", "Elec meter": "28609704"},
        {"Shop": "32", "Elec meter": "28609705"},
        {"Shop": "33", "Elec meter": "28609706"},
        {"Shop": "34", "Elec meter": "28609707"},
        {"Shop": "35", "Elec meter": "28609708"},
        {"Shop": "36", "Elec meter": "28609709"},
        {"Shop": "Office", "Elec meter": "28609686"},
    ]


DEFAULT_SHOP_METER_CATALOG = build_default_shop_meter_catalog()
APP_DISPLAY_NAME = "Clients Manager"
SPEC_FILE = APP_DIR / f"{APP_NAME}.spec"
PYTHON_SOURCE_FILES = sorted(
    path
    for path in SOURCE_DIR.rglob("*.py")
    if path.name not in {"test_clients_management.py", "tmp_debug.py", "verify_language_fix.py", "verify_ui.py"}
    and "__pycache__" not in path.parts
    and "build" not in path.parts
    and "dist" not in path.parts
)
PROJECT_SOURCE_MODULES = list(PYTHON_SOURCE_FILES)


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
COUNTRY_CODES_DATA = SOURCE_DIR / "config" / "country_codes.json"
SHOPS_ELECTRICAL_METERS_FILE = SOURCE_DIR / "config" / "Shops_Elect_meters.json"
CLIENTS_DATA_FILE = APP_DIR / "clients.json"
USERS_DATA_FILE = APP_DIR / "users.json"
GUESTS_DATA_FILE = APP_DIR / "guests.json"
DOCUMENTS_DATA_FILE = SOURCE_DIR / "config" / "docs" / "documents.txt"
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
    SOURCE_DIR / "config",
    SOURCE_DIR / "config" / "docs",
    CLIENTS_ROOT_DIR,
    *OUTPUT_LOG_DIRS,
]
REQUIRED_RUNTIME_DIRECTORIES = list(PROJECT_RUNTIME_DIRECTORIES)
LEGACY_APP_NAMES = ["marketing_booster", "marketing_booster_ar"]
LEGACY_DISPLAY_NAMES = ["Marketing Booster", "Marketing Booster AR", "Clients Manager", "Starco Commercial Complex"]
RUNTIME_DATA_FILES = [
    TARGET_ICON,
    CLIENTS_DATA_FILE,
    USERS_DATA_FILE,
    GUESTS_DATA_FILE,
    COUNTRY_CODES_DATA,
    SHOPS_ELECTRICAL_METERS_FILE,
    DOCUMENTS_DATA_FILE,
    SOURCE_DIR / "translations.py",
    STARCO_RENT_CONTRACT,
    *PROJECT_RUNTIME_DIRECTORIES,
]
RUNTIME_DATA_FILES = [path for path in RUNTIME_DATA_FILES if path is not None and path.exists()]


def validate_runtime_asset_catalog():
    required_paths = [
        ENTRY_SCRIPT,
        *PROJECT_SOURCE_MODULES,
        CLIENTS_DATA_FILE,
        USERS_DATA_FILE,
        GUESTS_DATA_FILE,
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

    ui_file = SOURCE_DIR / "ui" / "dashboard.py"
    ui_utils_file = SOURCE_DIR / "ui" / "utils.py"
    session_file = SOURCE_DIR / "ui" / "session.py"
    action_file = SOURCE_DIR / "ui" / "client_actions.py"
    translation_file = SOURCE_DIR / "config" / "translations.py"

    ui_content = ui_file.read_text(encoding="utf-8") if ui_file.exists() else ""
    ui_utils_content = ui_utils_file.read_text(encoding="utf-8") if ui_utils_file.exists() else ""
    session_content = session_file.read_text(encoding="utf-8") if session_file.exists() else ""
    action_content = action_file.read_text(encoding="utf-8") if action_file.exists() else ""
    translation_content = translation_file.read_text(encoding="utf-8") if translation_file.exists() else ""

    ui_markers = [
        "def set_language(lang):",
        "def T(text, **kwargs):",
        "def validate_translation_coverage():",
        "CURRENT_LANGUAGE = \"eng\"",
        "Logged in as: {user_name}",
        "Client Details",
    ]

    ui_utils_markers = [
        "def refresh_translatable_widget",
        "def set_emoji_translated_label",
        "def is_arabic_text",
        "def apply_bidi_text",
    ]

    session_markers = [
        "def ensure_default_guest_session():",
        "CURRENT_SESSION_PROFILE",
    ]

    action_markers = [
        "class ClientManagementMixin",
        "def switch_language(self, event=None):",
        "from config import translations as lang",
        "lang.set_language(selected)",
        "self.language_var.set(lang.CURRENT_LANGUAGE)",
        "self.refresh_lang_ui()",
    ]

    translation_markers = [
        "CURRENT_LANGUAGE = \"eng\"",
        "def set_language(lang):",
        "def T(text, **kwargs):",
        "def validate_translation_coverage():",
        "TRANSLATIONS = {",
        "\"Language\": \"Language\"",
    ]

    stale_ui_markers = [
        "def current_language(",
        "CURRENT_LANGUAGE = lang.CURRENT_LANGUAGE",
        "def T(key: str, **kwargs)",
        "def set_language(lang_code)",
        '"Guest user selected"',
        '"Logged in as {user_name}"',
    ]

    required_file_sets = [
        (ui_file, ui_markers),
        (action_file, action_markers),
        (translation_file, translation_markers),
    ]
    optional_file_sets = [
        (ui_utils_file, ui_utils_markers),
        (session_file, session_markers),
    ]
    file_contents = {
        ui_file: ui_content,
        ui_utils_file: ui_utils_content,
        session_file: session_content,
        action_file: action_content,
        translation_file: translation_content,
    }

    missing_by_file = []
    for file_path, markers in required_file_sets:
        if not file_path.exists():
            missing_by_file.append(f"{file_path.name}: missing file")
            continue
        for marker in markers:
            if marker not in file_contents[file_path]:
                missing_by_file.append(f"{file_path.name}: {marker}")

    for file_path, markers in optional_file_sets:
        if not file_path.exists():
            continue
        for marker in markers:
            if marker not in file_contents[file_path]:
                missing_by_file.append(f"{file_path.name}: {marker}")

    stale_markers = [marker for marker in stale_ui_markers if marker in ui_content]

    if stale_markers:
        details = "\n".join(f" - {marker}" for marker in stale_markers)
        raise RuntimeError(
            "Packaging aborted: stale duplicated language logic remains in the UI module.\n"
            f"Conflicting markers:\n{details}"
        )
    if missing_by_file:
        details = "\n".join(f" - {marker}" for marker in missing_by_file)
        raise RuntimeError(
            "Packaging aborted: the active app modules do not contain the expected language and RTL behavior.\n"
            f"Missing markers:\n{details}"
        )

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


def add_runtime_assets(cmd):
    for path in collect_runtime_assets():
        if not path.exists():
            continue
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


def normalize_payment_method(value):
    text = str(value or "").strip().lower()
    if not text:
        return "Cash"
    mapping = {
        "cash": "Cash",
        "cheque": "Cheque",
        "check": "Cheque",
        "bank transaction": "Bank Transaction",
        "bank_transaction": "Bank Transaction",
        "bank": "Bank Transaction",
        "bank transfer": "Bank Transaction",
    }
    return mapping.get(text, text.title())


def normalize_legacy_client_data(records):
    if not isinstance(records, list):
        return []

    migrated = []
    for item in records:
        if not isinstance(item, dict):
            continue

        normalized = dict(item)
        contract_details = None
        for key in ("contract_details", "contractDetails", "Contract Details"):
            candidate = normalized.get(key)
            if isinstance(candidate, dict):
                contract_details = dict(candidate)
                break

        if contract_details is None:
            contract_details = {}
        else:
            contract_details = dict(contract_details)

        default_contract = {
            "contract_number": "",
            "starting_date": "",
            "ending_date": "",
            "commercial_registration_number": "",
            "authorized_signature_name": "",
            "rent_value": "",
            "currency_type": "OMR",
            "open_issues": "",
            "duration_years": "",
            "renewable": "",
            "first_party": "",
            "second_party": "",
        }
        merged_contract = {**default_contract, **contract_details}
        merged_contract["currency_type"] = str(merged_contract.get("currency_type") or "").strip() or "OMR"
        normalized["contract_details"] = merged_contract

        for legacy_key in ("contractDetails", "Contract Details"):
            normalized.pop(legacy_key, None)

        transactions = normalized.get("transactions")
        if isinstance(transactions, list):
            normalized["transactions"] = [
                {
                    **entry,
                    "bank_transaction_details": str(entry.get("bank_transaction_details", "") or "").strip(),
                    "payment_method": normalize_payment_method(entry.get("payment_method", "Cash")),
                }
                if isinstance(entry, dict)
                else entry
                for entry in transactions
            ]

        migrated.append(normalized)
    return migrated


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

    def ensure_json_file(path, default_content, parser_ok=lambda payload: True):
        if not path.exists():
            path.write_text(default_content, encoding="utf-8")
            return

        try:
            content = path.read_text(encoding="utf-8")
            payload = json.loads(content) if content.strip() else None
        except (ValueError, TypeError):
            payload = None

        if payload is None or not parser_ok(payload):
            path.write_text(default_content, encoding="utf-8")

    ensure_json_file(CLIENTS_DATA_FILE, "[]", lambda payload: isinstance(payload, list))
    ensure_json_file(
        USERS_DATA_FILE,
        json.dumps({"users": []}, ensure_ascii=False, indent=2),
        lambda payload: isinstance(payload, dict) and isinstance(payload.get("users", []), list),
    )
    ensure_json_file(
        GUESTS_DATA_FILE,
        json.dumps({"guests": []}, ensure_ascii=False, indent=2),
        lambda payload: isinstance(payload, dict) and isinstance(payload.get("guests", []), list),
    )

    CLIENTS_ROOT_DIR.mkdir(parents=True, exist_ok=True)

    COUNTRY_CODES_DATA.parent.mkdir(parents=True, exist_ok=True)
    if not COUNTRY_CODES_DATA.exists():
        COUNTRY_CODES_DATA.write_text("[]", encoding="utf-8")

    SHOPS_ELECTRICAL_METERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SHOPS_ELECTRICAL_METERS_FILE.exists() or SHOPS_ELECTRICAL_METERS_FILE.stat().st_size == 0:
        SHOPS_ELECTRICAL_METERS_FILE.write_text(
            json.dumps(DEFAULT_SHOP_METER_CATALOG, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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
        "--hidden-import",
        "tkinter",
        "--hidden-import",
        "tkinter.ttk",
        "--hidden-import",
        "tkinter.messagebox",
        "--hidden-import",
        "tkinter.filedialog",
        "--hidden-import",
        "tkinter.simpledialog",
        "--hidden-import",
        "webbrowser",
        "--hidden-import",
        "bidi",
        "--hidden-import",
        "bidi.algorithm",
        "--hidden-import",
        "arabic_reshaper",
        "--hidden-import",
        "PIL",
        "--hidden-import",
        "PIL.Image",
        "--hidden-import",
        "PIL.ImageTk",
        "--collect-all",
        "tkinter",
        "--collect-all",
        "bidi",
        "--collect-all",
        "arabic_reshaper",
        "--collect-all",
        "PIL",
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
