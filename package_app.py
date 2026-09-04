import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
SOURCE_DIR = APP_DIR / "python code"
DIST_DIR = APP_DIR / "dist"
BUILD_DIR = APP_DIR / "build"
APP_NAME = "marketing_booster_ar"
APP_DISPLAY_NAME = "Marketing Booster AR"
SPEC_FILE = APP_DIR / f"{APP_NAME}.spec"
TARGET_ICON = APP_DIR / "starco_icon.ico"
LEGACY_APP_NAMES = ["marketing_booster"]
LEGACY_DISPLAY_NAMES = ["Marketing Booster"]


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
        ]
        for stale in stale_paths:
            if stale.exists():
                if stale.is_dir():
                    for child in stale.iterdir():
                        child.unlink()
                    stale.rmdir()
                else:
                    stale.unlink()

    for legacy_name in LEGACY_DISPLAY_NAMES:
        desktop_link = DESKTOP_DIR / f"{legacy_name}.lnk"
        if desktop_link.exists():
            desktop_link.unlink()

    desktop_link = DESKTOP_DIR / f"{APP_DISPLAY_NAME}.lnk"
    if desktop_link.exists():
        desktop_link.unlink()


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


def build_app():
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
        cmd.extend([
            "--icon",
            str(TARGET_ICON),
            "--add-data",
            f"{TARGET_ICON};.",
        ])

    cmd.append(str(SOURCE_DIR / "main.py"))

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
    shortcut.save()

    print(f"Shortcut created: {desktop_link}")
    return desktop_link


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("This packaging script is for Windows only.")

    exe = build_app()
    print(f"Built: {exe}")
    create_shortcut()
