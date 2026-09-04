import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clients_management import Client, ClientManager
from clients_progress_ui import Plan, parse_task_items
from sync_documents import TARGET

try:
    from package_app import resolve_desktop_dir
except ImportError:
    resolve_desktop_dir = None


class ClientManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = os.path.join(self.temp_dir.name, "clients.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_list_clients(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Bin Salim", "99999999", "machineries suppliers 'Hilti'")

        self.assertEqual(len(manager.clients), 1)
        self.assertEqual(manager.clients[0].name, "Bin Salim")
        self.assertIn("Bin Salim", manager.list_clients())

    def test_search_client(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Ali", "123456", "Stationery")
        manager.add_client("Sara", "654321", "Electronics")

        result = manager.search_clients("sara")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Sara")

    def test_save_and_load(self):
        manager = ClientManager(self.file_path)
        manager.add_client("John", "111", "IT")
        manager.save_clients()

        loaded = ClientManager(self.file_path)
        loaded.load_clients()

        self.assertEqual(len(loaded.clients), 1)
        self.assertEqual(loaded.clients[0].name, "John")

    def test_manager_starts_with_loaded_clients(self):
        manager = ClientManager(self.file_path)
        self.assertEqual(manager.clients, [])

        manager.add_client("Sarah", "777", "Design")
        self.assertEqual(len(manager.clients), 1)
        self.assertEqual(manager.clients[0].name, "Sarah")

    def test_add_client_with_email(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Nora", "555", "Consulting", "nora@example.com")

        self.assertEqual(manager.clients[0].email, "nora@example.com")
        self.assertEqual(manager.clients[0].to_dict()["email"], "nora@example.com")

    def test_delete_client_removes_selected_client(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Ali", "123", "Stationery")
        manager.add_client("Sara", "456", "Electronics")

        removed = manager.delete_client("Ali")

        self.assertTrue(removed)
        self.assertEqual(len(manager.clients), 1)
        self.assertEqual(manager.clients[0].name, "Sara")

    def test_plan_sync_keeps_pending_tasks_in_sync(self):
        plan = Plan(Client("Sam", "123", "Marketing"), all_tasks=["Task 1", "Task 2", "Task 3"])
        plan.pending_tasks = ["Task 1", "Task 3"]

        plan.sync_task_lists(all_tasks=["Task 1", "Task 2", "Task 3", "Task 4"], pending_tasks=["Task 2", "Task 4"])

        self.assertEqual(plan.all_tasks, ["Task 1", "Task 2", "Task 3", "Task 4"])
        self.assertEqual(plan.pending_tasks, ["Task 2", "Task 4"])

    def test_add_review_and_get_all_reviews(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Ali", "123456", "Stationery")

        added = manager.add_review("Ali", "Good follow-up and quick response.")

        self.assertTrue(added)
        self.assertEqual(len(manager.clients[0].reviews), 1)
        self.assertIn("Good follow-up and quick response.", manager.clients[0].reviews[0]["review"])

        all_reviews = manager.get_all_reviews()
        self.assertEqual(len(all_reviews), 1)
        self.assertEqual(all_reviews[0]["client_name"], "Ali")

    def test_parse_task_items_reads_comma_and_newline_lists(self):
        tasks = parse_task_items("Research, Design, Launch\nReview")
        self.assertEqual(tasks, ["Research", "Design", "Launch", "Review"])

        tasks = parse_task_items("", fallback_total=3)
        self.assertEqual(tasks, ["Task 1", "Task 2", "Task 3"])

    def test_resolve_desktop_dir_uses_existing_windows_desktop(self):
        if resolve_desktop_dir is None:
            self.fail("resolve_desktop_dir is not available")

        desktop_dir = resolve_desktop_dir()
        self.assertTrue(desktop_dir.exists())
        self.assertTrue(str(desktop_dir).endswith("Desktop") or str(desktop_dir).endswith("Desktop") or "Desktop" in str(desktop_dir))

    def test_sync_documents_target_uses_current_project_root(self):
        project_root = Path(__file__).resolve().parent.parent
        expected_target = project_root / "python code" / "docs" / "documents.txt"
        self.assertEqual(TARGET.resolve(), expected_target.resolve())


if __name__ == "__main__":
    unittest.main()
