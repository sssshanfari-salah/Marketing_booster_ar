import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def resolve_ui_file():
    for candidate in (ROOT / "python_code" / "clients_progress_ui.py", ROOT / "python code" / "clients_progress_ui.py"):
        if candidate.exists():
            return candidate
    return ROOT / "python_code" / "clients_progress_ui.py"


UI_FILE = resolve_ui_file()

print("Checking UI syntax...")
source = UI_FILE.read_text(encoding="utf-8")
ast.parse(source)
print("UI syntax OK")

PYTHON_DIR = ROOT / "python_code" if (ROOT / "python_code").exists() else ROOT / "python code"
sys.path.insert(0, str(PYTHON_DIR))
import clients_progress_ui as ui

assert hasattr(ui.ProgressApp, "export_client_log"), "missing export_client_log"
assert hasattr(ui.ProgressApp, "export_task_log"), "missing export_task_log"
assert hasattr(ui.ProgressApp, "export_observation_log"), "missing export_observation_log"
assert ui.resolve_log_output_dir("clients_logs").name == "clients_logs"
assert ui.resolve_log_output_dir("tasks_logs").name == "tasks_logs"
assert ui.resolve_log_output_dir("observation_logs").name == "observation_logs"
print("UI actions and output folders OK")
