import ast
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def resolve_source_dir():
    return APP_DIR / "python_code"


def resolve_reservation_contract_dir():
    """Return the sibling 'Reservation contract' project folder.

    This folder is the sole source of truth for client data, so no other
    legacy project folder is ever considered here.
    """
    parent_dir = APP_DIR.parent
    if not parent_dir.exists():
        return None

    for alias in (
        "Reservation contract",
        "Reservation_contract",
        "Reservation Contract",
        "Reservation-Contract",
    ):
        candidate = parent_dir / alias
        if candidate.is_dir():
            return candidate.resolve(strict=False)

    for child in parent_dir.iterdir():
        if child.is_dir():
            lower_name = child.name.lower()
            if "reservation" in lower_name and "contract" in lower_name:
                return child.resolve(strict=False)

    return None


def _copy_tree_merge(src_dir, dst_dir, skip_dirs=None):
    skip_dirs = set(skip_dirs or [])
    dst_dir.mkdir(parents=True, exist_ok=True)
    for child in src_dir.iterdir():
        if child.name in skip_dirs:
            continue
        dst_child = dst_dir / child.name
        if child.is_dir():
            if dst_child.exists() and not dst_child.is_dir():
                try:
                    dst_child.unlink()
                except OSError:
                    continue
            _copy_tree_merge(child, dst_child, skip_dirs=skip_dirs)
        else:
            dst_parent = dst_child.parent
            dst_parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(child, dst_child)
            except PermissionError:
                try:
                    os.chmod(dst_child, os.stat(dst_child).st_mode | 0o200)
                    shutil.copy2(child, dst_child)
                except OSError:
                    continue


def sync_source_of_truth_assets():
    source_root = resolve_reservation_contract_dir()
    if source_root is None:
        return

    items_to_copy = [
        "clients.json",
        "users.json",
        "guests.json",
        "python_code",
        "supporting_documents",
        "Clients",
        "starco_icon.ico",
        "starco icon",
    ]

    protected_runtime_dirs = {"clients_logs", "tasks_logs", "observation_logs"}
    for item_name in items_to_copy:
        src = source_root / item_name
        if not src.exists():
            continue
        dst = APP_DIR / item_name
        if src.is_dir():
            if dst.exists() and dst.is_file():
                try:
                    dst.unlink()
                except OSError:
                    continue
            _copy_tree_merge(src, dst, skip_dirs=protected_runtime_dirs if item_name == "python_code" else set())
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, dst)
            except PermissionError:
                try:
                    os.chmod(dst, os.stat(dst).st_mode | 0o200)
                    shutil.copy2(src, dst)
                except OSError:
                    continue

    application_outputs_src = source_root / "application_outputs"
    if application_outputs_src.exists():
        dest_dir = APP_DIR / "application_outputs"
        dest_dir.mkdir(parents=True, exist_ok=True)
        _copy_tree_merge(application_outputs_src, dest_dir, skip_dirs={"clients_logs", "tasks_logs", "observation_logs"})


def migrate_legacy_project_data_files():
    """Sync build-time data assets from the Reservation contract project.

    The Reservation contract project is the single source of truth for
    client data, so this only copies its assets in - it never merges in
    data from any other legacy project folder.
    """
    sync_source_of_truth_assets()


SOURCE_DIR = resolve_source_dir()
ENTRY_SCRIPT = SOURCE_DIR / "app" / "main.py"
DIST_DIR = APP_DIR / "dist"
BUILD_DIR = APP_DIR / "build"
APP_BASE_NAME = "marketing_booster_ar"
APP_VERSION = str(os.environ.get("APP_VERSION", "v2")).strip()
APP_NAME = str(os.environ.get("APP_TARGET_NAME", "")).strip() or (
    f"{APP_BASE_NAME}_{APP_VERSION}" if APP_VERSION else APP_BASE_NAME
)
APP_DISPLAY_NAME = str(os.environ.get("APP_DISPLAY_NAME", "")).strip() or (
    f"Clients Manager {APP_VERSION}" if APP_VERSION else "Clients Manager"
)


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
SPEC_FILE = APP_DIR / f"{APP_NAME}.spec"


def discover_package_imports():
    """Return all project packages/modules that should be bundled for frozen builds."""
    package_roots = [
        ("python_code", APP_DIR / "python_code"),
        ("logic", SOURCE_DIR / "logic"),
        ("ui", SOURCE_DIR / "ui"),
        ("config", SOURCE_DIR / "config"),
    ]

    discovered = {
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "tkinter.filedialog",
        "tkinter.simpledialog",
        "tkinter.font",
        "tkinter.constants",
        "tkinter.commondialog",
        "tkinter.colorchooser",
        "webbrowser",
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "PIL._imaging",
        "PIL._imagingtk",
        "bidi",
        "bidi.algorithm",
        "arabic_reshaper",
        "logic",
        "ui",
        "config",
        "python_code",
        "win32com",
        "win32com.client",
        "json",
        "pathlib",
        "email",
        "multiprocessing",
        "queue",
        "threading",
        "urllib.request",
        "csv",
        "datetime",
        "tempfile",
        "shutil",
        "sqlite3",
        "importlib",
        "importlib.util",
        "typing",
    }

    def record_module_name(module_name):
        if not module_name:
            return
        stripped = str(module_name).strip()
        if not stripped:
            return
        discovered.add(stripped)
        parts = stripped.split(".")
        for index in range(1, len(parts)):
            discovered.add(".".join(parts[:index]))

    def record_aliases_from_ast(source_path):
        try:
            source = source_path.read_text(encoding="utf-8")
        except OSError:
            return
        try:
            parsed = ast.parse(source, filename=str(source_path))
        except SyntaxError:
            return

        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name:
                        record_module_name(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    record_module_name(node.module)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "import_module":
                    if isinstance(func.value, ast.Name) and func.value.id == "importlib":
                        if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                            record_module_name(node.args[0].value)
                elif isinstance(func, ast.Name) and func.id == "__import__":
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        record_module_name(node.args[0].value)

    for root_name, root_dir in package_roots:
        if not root_dir.exists():
            continue
        for path in sorted(root_dir.rglob("*.py")):
            if any(part in {"__pycache__", "build", "dist"} for part in path.parts):
                continue
            if path.name.startswith("test_"):
                continue
            relative_parts = path.relative_to(root_dir).with_suffix("").parts
            if relative_parts and relative_parts[-1] == "__init__":
                module_name = root_name
            else:
                module_name = ".".join([root_name, *relative_parts])
            record_module_name(module_name)
            record_aliases_from_ast(path)

    for root_dir in (APP_DIR / "python_code",):
        if not root_dir.exists():
            continue
        for path in sorted(root_dir.rglob("*.py")):
            if any(part in {"__pycache__", "build", "dist"} for part in path.parts):
                continue
            if path.name.startswith("test_"):
                continue
            record_aliases_from_ast(path)

    return sorted(discovered)


EXPLICIT_HIDDEN_IMPORTS = {
    "python_code",
    "python_code.app",
    "python_code.app.main",
    "python_code.config",
    "python_code.config.language_compat",
        "python_code.logic",
    "python_code.logic.clients_management",
    "python_code.logic.shop_management",
    "python_code.logic.shops_conversion_to_dic",
    "python_code.logic.months",
    "python_code.logic.business_logic",
    "python_code.logic.validations",
    "python_code.logic.validations.Storage",
    "python_code.logic.validations.Storage.client_storage",
    "python_code.logic.validations.Storage.reports",
    "python_code.logic.validations.Storage.reports.client_payment_report",
    "python_code.logic.starco_finance",
    "python_code.ui",
    "python_code.ui.dashboard",
    "python_code.ui.client_actions",
    "python_code.ui.contract_format",
    "python_code.ui.contract_format_ar",
    "python_code.ui.main_app",
    "python_code.ui.reservation_contract",
    "python_code.ui.session",
    "python_code.ui.shared",
    "python_code.ui.utils",
    "config",
    "config.language_compat",
        "logic",
    "logic.clients_management",
    "logic.shop_management",
    "logic.shops_conversion_to_dic",
    "logic.months",
    "logic.business_logic",
    "logic.validations",
    "logic.validations.Storage",
    "logic.validations.Storage.client_storage",
    "logic.validations.Storage.reports",
    "logic.validations.Storage.reports.client_payment_report",
    "logic.starco_finance",
    "ui",
    "ui.dashboard",
    "ui.client_actions",
    "ui.contract_format",
    "ui.contract_format_ar",
    "ui.main_app",
    "ui.reservation_contract",
    "ui.session",
    "ui.shared",
    "ui.utils",
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "tkinter.filedialog",
    "tkinter.simpledialog",
    "tkinter.font",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "bidi",
    "bidi.algorithm",
    "arabic_reshaper",
    "win32print",
    "win32com",
    "win32com.client",
}

PACKAGING_HIDDEN_IMPORTS = sorted(set(discover_package_imports()) | EXPLICIT_HIDDEN_IMPORTS)
PACKAGING_SUBMODULE_ROOTS = tuple(
    item for item in sorted({name for name in PACKAGING_HIDDEN_IMPORTS if name and "." not in name})
    if item in {"logic", "ui", "config", "python_code"}
)
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
        SOURCE_DIR / "starco_icons" / "starco_icon2.ico",
        APP_DIR / "starco_icon2.ico",
        APP_DIR / "starco_icon.ico",
        APP_DIR / "starco icon" / "starco_icon2.ico",
        APP_DIR / "starco icon" / "starco_icon.ico",
        APP_DIR / "starco icon" / "icon.ico",
        APP_DIR / "starco icon" / "app_icon.ico",
        SOURCE_DIR / "starco_icon2.ico",
        SOURCE_DIR / "starco_icon.ico",
        SOURCE_DIR / "ui" / "icons" / "starco_icon2.ico",
        SOURCE_DIR / "ui" / "icons" / "starco_icon.ico",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return APP_DIR / "starco_icon2.ico"


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
    SOURCE_DIR / "config" / "language_compat.py",
    STARCO_RENT_CONTRACT,
    # Bundle legacy icon assets when present, but do not require the folder.
    APP_DIR / "starco icon",
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
    translation_file = SOURCE_DIR / "config" / "language_compat.py"
    client_manager_file = SOURCE_DIR / "logic" / "clients_management.py"

    ui_content = ui_file.read_text(encoding="utf-8") if ui_file.exists() else ""
    ui_utils_content = ui_utils_file.read_text(encoding="utf-8") if ui_utils_file.exists() else ""
    session_content = session_file.read_text(encoding="utf-8") if session_file.exists() else ""
    action_content = action_file.read_text(encoding="utf-8") if action_file.exists() else ""
    translation_content = translation_file.read_text(encoding="utf-8") if translation_file.exists() else ""
    client_manager_content = client_manager_file.read_text(encoding="utf-8") if client_manager_file.exists() else ""
    shop_management_file = SOURCE_DIR / "logic" / "shop_management.py"
    shop_management_content = shop_management_file.read_text(encoding="utf-8") if shop_management_file.exists() else ""
    finance_file = SOURCE_DIR / "logic" / "starco_finance.py"
    finance_content = finance_file.read_text(encoding="utf-8") if finance_file.exists() else ""

    ui_markers = [
        "from logic.validations.Storage.reports.client_payment_report import build_client_payment_report_text",
        "import config.language_compat as translations_core",
        "from config.language_compat import (",
        "CURRENT_LANGUAGE,",
        "T,",
        "apply_bidi_text,",
        "configure_emoji_label,",
        "get_emoji_font_families,",
        "is_arabic_text,",
        "refresh_translatable_widget,",
        "refresh_translatable_widgets,",
        "set_emoji_translated_label,",
        "set_language,",
        "validate_translation_coverage,",
        "def refresh_lang_ui(self):",
        "refresh_translatable_widgets(self)",
        "def safe_main():",
        "def is_desktop_environment_available():",
        "Headless mode detected: Tkinter GUI startup skipped because no desktop session is available.",
        "Runtime startup issue after window creation: a GUI callback failed during startup.",
        "selected_code = translations_core.resolve_language_code(selected)",
        "set_language(selected_code)",
        "def update_window_login_status(window, profile=None):",
        "window.login_status_var.set(display_name)",
        "Client Details",
        "self.selected_shops = remove_shop_from_selected_shops(self.selected_shops, deleted_shop_number)",
        "def select_all_clients(self):",
        "self.tree.configure(selectmode=\"extended\")",
        "self.tree.bind(\"<Control-a>\", lambda event: self.select_all_clients())",
        "def rebuild_selected_shops_from_clients(self):",
        "self.rebuild_selected_shops_from_clients()",
        "self.manager.validate_shop_number(shop_number, exclude_name=name)",
        "self.selected_shops.append({\n                \"Shop\": shop_number,\n                \"Elec meter\": str(getattr(client, \"electrical_meter\", \"\") or getattr(client, \"notes\", \"\") or \"\"),\n            })",
        "if not names or current_name not in names:\n            self.client_name_var.set(\"\")\n            self.client_combo.set(\"\")\n            return",
        "Select Client",
        "state=\"readonly\"",
        "def _save_client_progress(self):",
    ]

    ui_utils_markers = [
        "refresh_translatable_widget",
        "set_emoji_translated_label",
        "is_arabic_text",
        "apply_bidi_text",
    ]

    session_markers = [
        "def ensure_default_guest_session():",
        "CURRENT_SESSION_PROFILE",
    ]

    action_markers = [
        "class ClientManagementMixin",
        "def switch_language(self, event=None):",
        "from config import language_compat as lang",
        "selected = self.language_var.get()",
        "lang.set_language(lang.resolve_language_code(selected))",
        "self.language_var.set(lang.get_language_display_label(lang.CURRENT_LANGUAGE))",
        "self.refresh_lang_ui()",
    ]

    # The current compatibility layer replaces the removed translation catalog.
    translation_markers = [
        "CURRENT_LANGUAGE = \"eng\"",
        "def resolve_language_code(value):",
        "def set_language(value):",
        "def get_language_display_label(lang=None):",
        "def validate_translation_coverage(*args, **kwargs):",
        "def get_emoji_font_families():",
        "def configure_emoji_label(widget, text, *, size=10, bold=False):",
        "def set_emoji_translated_label(widget, original_text, emoji_prefix=\"\"):",
        "def refresh_translatable_widget(widget, original_text, emoji_prefix=\"\", *, size=10, bold=False):",
        "def refresh_translatable_widgets(target, *, labels=None, buttons=None):",
        "def is_arabic_text(value):",
        "def apply_bidi_text(value):",
        "def T(text, **kwargs):",
    ]

    client_manager_markers = [
        "from logic.shop_management import ShopManagementMixin, normalize_shop_numbers",
        "class ClientManager(ShopManagementMixin):",
        "from logic.models.transactions import normalize_transaction_entry as normalize_transaction_entry",
        "from logic.models.reservations import normalize_reservation_status as normalize_reservation_status",
        "from logic.validations.Storage.client_storage import (",
        "from logic.models.transactions import normalize_transaction_entry as normalize_transaction_entry",
        "def build_clients_report_text(file_path):",
    ]

    shop_management_markers = [
        "def normalize_shop_numbers(value)",
        "class ShopManagementMixin:",
        "def validate_shop_number(self,",
        "def get_used_shop_numbers(self,",
        "def get_available_shop_numbers(self,",
        "def create_client_directory(self, client)",
    ]
    finance_markers = [
        "from logic.models.transactions import normalize_transaction_entry as normalize_transaction_entry",
        "from logic.models.contracts import normalize_contract_details as normalize_contract_details",
        "from logic.models.reservations import normalize_reservation_status as normalize_reservation_status",
        "class ClientTransactionsWindow(tk.Toplevel):",
        "class ReservationStatusWindow(tk.Toplevel):",
    ]

    shop_validation_file = SOURCE_DIR / "logic" / "shops_conversion_to_dic.py"
    shop_validation_content = shop_validation_file.read_text(encoding="utf-8") if shop_validation_file.exists() else ""
    shop_validation_markers = [
        "def validate_shop(shop, selected=None):",
        "authoritative_selected = _load_authoritative_selected_shops()",
        "if authoritative_selected:",
        "selected = authoritative_selected",
    ]

    stale_ui_markers = [
        "def current_language(",
        "CURRENT_LANGUAGE = lang.CURRENT_LANGUAGE",
        "def set_language(lang_code)",
        "from python_code.ui.utils import",
        "from ui.utils import",
        '"Guest user selected"',
        '"Logged in as {user_name}"',
        "Logged in as: {user_name}",
        "from config import translations as translations_core",
        "from config import translations as lang",
        "from config.translations import",
        "import config.translations",
        # Client-detail editing was intentionally removed from the dashboard; the
        # Reservation Contract form is now the sole place to edit client details.
        'T("Add Client")',
        'T("Save Client")',
        "def add_new_client(self):",
        "def save_current_client(self):",
    ]

    required_file_sets = [
        (ui_file, ui_markers),
        (action_file, action_markers),
        (translation_file, translation_markers),
        (client_manager_file, client_manager_markers),
        (shop_management_file, shop_management_markers),
        (finance_file, finance_markers),
        (shop_validation_file, shop_validation_markers),
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
        client_manager_file: client_manager_content,
        shop_management_file: shop_management_content,
        finance_file: finance_content,
        shop_validation_file: shop_validation_content,
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
            "Packaging aborted: stale language imports or duplicated logic remain in the UI module.\n"
            f"Conflicting markers:\n{details}"
        )
    if missing_by_file:
        details = "\n".join(f" - {marker}" for marker in missing_by_file)
        raise RuntimeError(
            "Packaging aborted: the active app modules do not contain the expected runtime behavior.\n"
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
    if value is None:
        return "Cash"

    text = str(value).strip()
    if not text:
        return "Cash"

    normalized = text.lower()
    choices = ("Cash", "Cheque", "Bank Transaction")
    lookup = {choice.lower(): choice for choice in choices}
    if normalized in lookup:
        return lookup[normalized]

    for choice in choices:
        if normalized in choice.lower():
            return choice

    for alias in ("check", "bank_transaction", "bank transfer", "bank-transfer", "bank"):
        if normalized == alias:
            return "Bank Transaction"

    return "Cash"


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


def run_in_packaging_environment():
    """Relaunch managed/prerelease Python in a local stable Python 3.14 venv."""
    if sys.prefix != sys.base_prefix and sys.version_info.releaselevel == "final":
        return None

    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError(
            "Packaging requires a virtual environment with a stable Python release. "
            "Install uv and Python 3.14, or create a virtual environment manually "
            "and run package_app.py with its Python interpreter."
        )

    environment_dir = APP_DIR / ".venv-package"
    interpreter = environment_dir / "Scripts" / "python.exe"
    if not interpreter.exists():
        print("Creating an isolated Python 3.14 packaging environment...", flush=True)
        subprocess.check_call([
            uv, "venv", "--python", "3.14", "--no-python-downloads",
            str(environment_dir),
        ])

    version = json.loads(subprocess.check_output(
        [str(interpreter), "-c",
         "import json, sys; print(json.dumps(list(sys.version_info)))"],
        text=True,
    ))
    if version[:2] != [3, 14] or version[3] != "final":
        raise RuntimeError(
            f"Expected stable Python 3.14 in {environment_dir}, got {version}. "
            "Use a Python 3.14 virtual environment to run package_app.py."
        )

    print(f"Using packaging interpreter: {interpreter}", flush=True)
    return subprocess.run(
        [str(interpreter), str(Path(__file__).resolve()), *sys.argv[1:]],
        cwd=str(APP_DIR),
        check=False,
    ).returncode


def ensure_packaging_dependencies():
    required_packages = [
        "pyinstaller",
        "pillow",
        "python-bidi",
        "arabic-reshaper",
    ]
    missing = []

    for package in required_packages:
        try:
            if package == "pyinstaller":
                import PyInstaller  # noqa: F401
            elif package == "pillow":
                import PIL  # noqa: F401
            elif package == "python-bidi":
                import bidi  # noqa: F401
            elif package == "arabic-reshaper":
                import arabic_reshaper  # noqa: F401
        except ModuleNotFoundError:
            missing.append(package)

    if missing:
        if sys.prefix == sys.base_prefix:
            raise RuntimeError(
                "Cannot install packaging dependencies outside a virtual environment. "
                "Run package_app.py directly to create its isolated packaging environment."
            )
        print(f"Installing packaging dependencies: {', '.join(missing)}")
        uv = shutil.which("uv")
        if uv is not None:
            subprocess.check_call([uv, "pip", "install", "--python", sys.executable, *missing])
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])


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


def terminate_stale_build_processes():
    process_name_patterns = [
        APP_NAME,
        APP_BASE_NAME,
        f"{APP_NAME}.exe",
        f"{APP_BASE_NAME}.exe",
    ]
    unique_names = sorted({str(name).strip() for name in process_name_patterns if str(name).strip()})
    name_pattern = "|".join(re.escape(name) for name in unique_names)
    commandline_pattern = "|".join(re.escape(name) for name in unique_names if name.endswith(".exe"))
    if not commandline_pattern:
        return
    try:
        output = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                (
                    "Get-CimInstance Win32_Process | Where-Object { "
                    "$_.Name -match '" + name_pattern + "' -or $_.CommandLine -match '(?i)(?:^|[\\\\/])(" + commandline_pattern + ")(?:$|[\\\"\\s])' "
                    "} | Select-Object -ExpandProperty ProcessId"
                ),
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return

    for raw_pid in output.splitlines():
        try:
            pid = int(str(raw_pid).strip())
        except ValueError:
            continue
        if pid <= 0:
            continue
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass


def remove_directory(path):
    if not path.exists():
        return
    try:
        force_remove_path(path)
    except (PermissionError, OSError):
        print(f"Warning: could not fully remove {path}. Continuing with the rebuild attempt.")


def ensure_runtime_files():
    migrate_legacy_project_data_files()
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
    ensure_packaging_dependencies()
    ensure_runtime_files()
    validate_runtime_asset_catalog()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    terminate_stale_build_processes()
    remove_stale_artifacts()
    remove_directory(BUILD_DIR)
    remove_directory(DIST_DIR)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    if SPEC_FILE.exists():
        SPEC_FILE.unlink()

    if not ENTRY_SCRIPT.exists():
        raise FileNotFoundError(f"Entry script missing: {ENTRY_SCRIPT}")

    # Use PYINSTALLER_CONSOLE_FALLBACK when building in CI, remote shells, or any headless
    # environment that needs a console-capable executable for logs and diagnostics.
    # Leave it unset for the normal desktop GUI build, which remains windowed.
    console_fallback_enabled = str(os.environ.get("PYINSTALLER_CONSOLE_FALLBACK", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    window_mode_flag = "--console" if console_fallback_enabled else "--windowed"

    if console_fallback_enabled:
        print("PyInstaller console fallback enabled for headless/CI execution.")
    else:
        print("PyInstaller desktop packaging mode enabled (windowed GUI).")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--onefile",
        window_mode_flag,
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(APP_DIR),
        "--paths",
        str(SOURCE_DIR),
        "--paths",
        str(APP_DIR),
    ]

    for hidden_import in PACKAGING_HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", hidden_import])

    for package_name in PACKAGING_SUBMODULE_ROOTS:
        cmd.extend(["--collect-submodules", package_name])

    for package_name in sorted({
        name for name in PACKAGING_HIDDEN_IMPORTS
        if name.startswith(("logic.", "ui.", "config.", "python_code."))
    }):
        cmd.extend(["--collect-submodules", package_name])

    cmd.extend([
        "--collect-all",
        "tkinter",
        "--collect-all",
        "bidi",
        "--collect-all",
        "arabic_reshaper",
        "--collect-all",
        "PIL",
    ])

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

    environment_exit_code = run_in_packaging_environment()
    if environment_exit_code is not None:
        raise SystemExit(environment_exit_code)

    exe = build_app()
    if exe is None:
        raise SystemExit("App build failed.")

    print(f"Built: {exe}")
    shortcut = create_shortcut()
    if shortcut is not None:
        print(f"Desktop shortcut: {shortcut}")
