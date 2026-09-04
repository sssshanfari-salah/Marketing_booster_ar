import os
import sys
import subprocess
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
SOURCE_DIR = APP_DIR / "python code"
DIST_DIR = APP_DIR / "dist"
BUILD_DIR = APP_DIR / "build"
APP_NAME = "marketing_booster_ar"
APP_DISPLAY_NAME = "Marketing Booster"
SPEC_FILE = APP_DIR / f"{APP_NAME}.spec"
TARGET_ICON = APP_DIR / "starco_icon.ico"


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


def build_app():
    if not ensure_pyinstaller():
        print("PyInstaller is not installed. Installing it now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
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
        str(SOURCE_DIR / "main.py"),
    ]

    if TARGET_ICON.exists():
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--windowed",
            "--name",
            APP_NAME,
            "--icon",
            str(TARGET_ICON),
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(BUILD_DIR),
            "--specpath",
            str(APP_DIR),
            str(SOURCE_DIR / "main.py"),
        ]

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
