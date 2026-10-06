import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for candidate in (str(PROJECT_ROOT), str(PROJECT_ROOT / "python_code")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

try:
    from logic.business_logic import Plan, parse_task_items, strip_task_number_prefix
except Exception:  # pragma: no cover - fallback for direct-file execution
    class Plan:
        Clients_progress = {}

        def __init__(self, client, all_tasks=None):
            self.client = client
            self.client_name = getattr(client, "name", "")
            self.all_tasks = list(all_tasks) if all_tasks is not None else []
            self.pending_tasks = list(self.all_tasks)
            self.progress = 0
            self.refresh_progress()

        def refresh_progress(self):
            if not self.all_tasks:
                self.progress = 100
                return self.progress
            remaining = len(self.pending_tasks)
            completed = len(self.all_tasks) - remaining
            self.progress = round((completed / len(self.all_tasks)) * 100)
            return self.progress

        def sync_task_lists(self, all_tasks=None, pending_tasks=None):
            if all_tasks is not None:
                self.all_tasks = list(all_tasks)
            if pending_tasks is not None:
                self.pending_tasks = list(pending_tasks)
            elif not self.pending_tasks:
                self.pending_tasks = list(self.all_tasks)
            self.pending_tasks = [task for task in self.pending_tasks if task in self.all_tasks]
            self.pending_tasks = list(dict.fromkeys(self.pending_tasks))
            self.all_tasks = list(dict.fromkeys(self.all_tasks))
            self.refresh_progress()
            self.update_clients_progress()

        def add_pending_task(self, task):
            if not task:
                return
            if task not in self.all_tasks:
                self.all_tasks.append(task)
            if task not in self.pending_tasks:
                self.pending_tasks.append(task)
            self.refresh_progress()
            self.update_clients_progress()

        def complete_task(self, task):
            if task in self.pending_tasks:
                self.pending_tasks.remove(task)
            self.refresh_progress()
            self.update_clients_progress()

        def update_clients_progress(self):
            self.refresh_progress()
            progress_data = {
                "client_name": getattr(self.client, "name", self.client_name),
                "progress": self.progress,
                "pending_tasks": list(self.pending_tasks),
                "all_tasks": list(self.all_tasks),
            }
            Plan.Clients_progress[getattr(self.client, "name", self.client_name)] = progress_data

        def to_dict(self):
            return {
                "client_name": self.client_name,
                "progress": self.progress,
                "pending_tasks": list(self.pending_tasks),
                "all_tasks": list(self.all_tasks),
            }

        def progress_color(self):
            width = 30
            filled = int((self.progress / 100) * width)
            bar = "█" * filled + " " * (width - filled)
            return f"|{bar}| {self.progress}%\nPending tasks: {len(self.pending_tasks)}"

    def parse_task_items(raw_value, fallback_total=0):
        import re
        text = (raw_value or "").strip()
        if not text:
            if fallback_total <= 0:
                return []
            return [str(i) for i in range(1, fallback_total + 1)]
        items = []
        for chunk in re.split(r"[\n,;]+", text):
            task = chunk.strip()
            if task.startswith("1.") or task.startswith("2.") or task.startswith("3."):
                task = re.sub(r"^\s*\d+\s*(?:[\.)\-:\]|]|\-\s*)\s*", "", task)
            task = task.strip()
            if task:
                items.append(task)
        return items

    def strip_task_number_prefix(task):
        import re
        text = str(task or "").strip()
        if not text:
            return ""
        return re.sub(r"^\s*\d+\s*(?:[\.)\-:\]|]|\-\s*)\s*", "", text).strip()

plan = Plan

__all__ = ["Plan", "plan", "parse_task_items", "strip_task_number_prefix"]
