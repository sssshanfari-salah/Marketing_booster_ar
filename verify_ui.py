import ast
import os
import sys
from pathlib import Path

ROOT = Path(r"c:/Users/ssssh/OneDrive/Documents/Marketing_booster_ar")
UI_FILE = ROOT / "python code" / "clients_progress_ui.py"

print("Checking UI syntax...")
source = UI_FILE.read_text(encoding="utf-8")
ast.parse(source)
print("UI syntax OK")

sys.path.insert(0, str(ROOT / "python code"))
import clients_progress_ui as ui

assert hasattr(ui.ProgressApp, "export_client_log"), "missing export_client_log"
assert hasattr(ui.ProgressApp, "export_task_log"), "missing export_task_log"
assert hasattr(ui.ProgressApp, "export_observation_log"), "missing export_observation_log"
assert ui.resolve_log_output_dir("clients_logs").name == "clients_logs"
assert ui.resolve_log_output_dir("tasks_logs").name == "tasks_logs"
assert ui.resolve_log_output_dir("observation_logs").name == "observation_logs"
print("UI actions and output folders OK")
