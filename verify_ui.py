"""Package-aware smoke test for the dashboard UI module."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python_code.ui import dashboard as ui

assert hasattr(ui.ProgressApp, "export_client_log"), "missing export_client_log"
assert hasattr(ui.ProgressApp, "export_task_log"), "missing export_task_log"
assert hasattr(ui.ProgressApp, "export_observation_log"), "missing export_observation_log"
assert ui.resolve_log_output_dir("clients_logs").name == "clients_logs"
assert ui.resolve_log_output_dir("tasks_logs").name == "tasks_logs"
assert ui.resolve_log_output_dir("observation_logs").name == "observation_logs"
print("verify_ui OK")
