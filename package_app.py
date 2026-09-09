import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
SOURCE_DIR = APP_DIR / "python code"
ENTRY_SCRIPT = SOURCE_DIR / "main.py"
DIST_DIR = APP_DIR / "dist"
BUILD_DIR = APP_DIR / "build"
APP_NAME = "marketing_booster_ar"
APP_DISPLAY_NAME = "Starco Commercial Complex"
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
CLIENTS_DATA_FILE = APP_DIR / "clients.json"
DOCUMENTS_DATA_FILE = SOURCE_DIR / "docs" / "documents.txt"
SUPPORTING_DOCUMENTS_DIR = APP_DIR / "supporting_documents"
STARCO_RENT_CONTRACT = SUPPORTING_DOCUMENTS_DIR / "starco_rent_contract_1.pdf"
APPLICATION_OUTPUTS_DIR = APP_DIR / "application_outputs"
CLIENT_LOGS_DIR = APPLICATION_OUTPUTS_DIR / "clients_logs"
TASK_LOGS_DIR = APPLICATION_OUTPUTS_DIR / "tasks_logs"
OBSERVATION_LOGS_DIR = APPLICATION_OUTPUTS_DIR / "observation_logs"
OUTPUT_LOG_DIRS = [APPLICATION_OUTPUTS_DIR, CLIENT_LOGS_DIR, TASK_LOGS_DIR, OBSERVATION_LOGS_DIR]
LEGACY_APP_NAMES = ["marketing_booster", "marketing_booster_ar"]
LEGACY_DISPLAY_NAMES = ["Marketing Booster", "Marketing Booster AR", "Clients Manager", "Starco Commercial Complex"]
RUNTIME_DATA_FILES = [
    TARGET_ICON,
    CLIENTS_DATA_FILE,
    COUNTRY_CODES_DATA,
    DOCUMENTS_DATA_FILE,
    STARCO_RENT_CONTRACT,
    *OUTPUT_LOG_DIRS,
]

# Keep the packaged app aligned with the current client-manager UI/data model.
RUNTIME_DATA_FILES = [path for path in RUNTIME_DATA_FILES if path is not None and path.exists()]


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

    if not CLIENTS_DATA_FILE.exists():
        CLIENTS_DATA_FILE.write_text("[]", encoding="utf-8")

    COUNTRY_CODES_DATA.parent.mkdir(parents=True, exist_ok=True)
    if not COUNTRY_CODES_DATA.exists():
        COUNTRY_CODES_DATA.write_text("[]", encoding="utf-8")

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

    runtime_files = [
        TARGET_ICON,
        CLIENTS_DATA_FILE,
        COUNTRY_CODES_DATA,
        DOCUMENTS_DATA_FILE,
        STARCO_RENT_CONTRACT,
        *OUTPUT_LOG_DIRS,
    ]
    for data_file in runtime_files:
        if data_file.exists():
            cmd.extend(["--add-data", f"{data_file}{os.pathsep}."])

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
