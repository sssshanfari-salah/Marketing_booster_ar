import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clients_management import Client, ClientManager, build_clients_report_text, format_contact_number
from clients_progress_ui import (
    Plan,
    ProgressApp,
    T,
    get_emoji_font_families,
    parse_task_items,
    resolve_log_output_dir,
    set_language,
    strip_task_number_prefix,
)
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

    def test_load_client_data_with_ui_like_field_names(self):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump([
                {
                    "Client Name": "Noura",
                    "Contact": "5551234",
                    "Business": "Boutique",
                    "Email": "noura@example.com",
                    "Shop Number": "12",
                    "reviews": [{"date": "2026-09-08", "review": "Great service"}]
                }
            ], file)

        manager = ClientManager(self.file_path)
        self.assertEqual(len(manager.clients), 1)
        self.assertEqual(manager.clients[0].name, "Noura")
        self.assertEqual(manager.clients[0].contact, "+9685551234")
        self.assertEqual(manager.clients[0].business, "Boutique")
        self.assertEqual(manager.clients[0].email, "noura@example.com")
        self.assertEqual(manager.clients[0].shop_number, "12")
        self.assertEqual(manager.clients[0].reviews[0]["review"], "Great service")

    def test_contact_numbers_default_to_oman_country_code(self):
        self.assertEqual(format_contact_number("5551234"), "+9685551234")

        manager = ClientManager(self.file_path)
        manager.add_client("Nora", "5551234", "Consulting", "nora@example.com")

        self.assertEqual(manager.clients[0].contact, "+9685551234")
        self.assertEqual(manager.clients[0].to_dict()["contact"], "+9685551234")

    def test_client_export_formats_are_share_ready(self):
        client = Client("Nora", "0555123456", "Consulting", "nora@example.com", "12")

        text = client.share_text()
        self.assertIn("Nora", text)
        self.assertIn("+968555123456", text)
        self.assertIn("nora@example.com", text)

        vcard = client.to_vcard()
        self.assertIn("BEGIN:VCARD", vcard)
        self.assertIn("FN:Nora", vcard)
        self.assertIn("TEL;TYPE=CELL:+968555123456", vcard)
        self.assertIn("EMAIL:nora@example.com", vcard)

    def test_client_progress_persists_with_client_record(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Ali", "123456", "Retail")

        manager.clients[0].progress = {
            "client_name": "Ali",
            "progress": 50,
            "pending_tasks": ["Follow up"],
            "all_tasks": ["Follow up", "Send invoice"],
        }
        manager.save_clients()

        reloaded = ClientManager(self.file_path)
        self.assertEqual(reloaded.clients[0].progress["progress"], 50)
        self.assertEqual(reloaded.clients[0].progress["pending_tasks"], ["Follow up"])
        self.assertIn("Send invoice", reloaded.clients[0].progress["all_tasks"])

    def test_build_clients_report_text_has_all_client_details(self):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump([
                {
                    "name": "Ali",
                    "contact": "+96891234567",
                    "business": "Consulting",
                    "email": "ali@example.com",
                    "shop_number": "12",
                    "reviews": [{"date": "2026-09-08", "review": "Good client"}],
                    "contract_details": {
                        "starting_date": "2026-01-01",
                        "ending_date": "2027-01-01",
                        "contract_number": "CN-001",
                    },
                }
            ], file)

        report = build_clients_report_text(self.file_path)
        self.assertIn("Clients Log", report)
        self.assertIn("Ali", report)
        self.assertIn("+96891234567", report)
        self.assertIn("Good client", report)
        self.assertIn("Starting Date", report)
        self.assertIn("2026-01-01", report)
        self.assertIn("Ending Date", report)
        self.assertIn("2027-01-01", report)
        self.assertIn("Contract Number", report)

    def test_add_client_with_email(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Nora", "555", "Consulting", "nora@example.com")

        self.assertEqual(manager.clients[0].email, "nora@example.com")
        self.assertEqual(manager.clients[0].to_dict()["email"], "nora@example.com")

    def test_duplicate_contact_number_is_rejected(self):
        manager = ClientManager(self.file_path)
        self.assertTrue(manager.add_client("Ali", "5551234", "Stationery"))
        self.assertFalse(manager.add_client("Sara", "5551234", "Electronics"))
        self.assertEqual(len(manager.clients), 1)
        self.assertEqual(manager.clients[0].name, "Ali")

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

    def test_update_review_comment_matches_numbered_display_text(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Ali", "123456", "Stationery")
        manager.add_review("Ali", "Good follow-up and quick response.")

        updated = manager.update_review_comment("Ali", "1. Good follow-up and quick response.", "Follow-up completed")

        self.assertTrue(updated)
        self.assertEqual(manager.clients[0].reviews[0]["comment"], "Follow-up completed")

    def test_parse_task_items_reads_comma_and_newline_lists(self):
        tasks = parse_task_items("Research, Design, Launch\nReview")
        self.assertEqual(tasks, ["Research", "Design", "Launch", "Review"])

        tasks = parse_task_items("", fallback_total=3)
        self.assertEqual(tasks, ["1", "2", "3"])

    def test_parse_task_items_handles_numbered_bullet_entries(self):
        tasks = parse_task_items("1. Research\n2. Design\n3) Launch")
        self.assertEqual(tasks, ["Research", "Design", "Launch"])

        self.assertEqual(parse_task_items("1) Review, 2) Final")[0], "Review")

    def test_strip_task_number_prefix_handles_numbered_entries(self):
        self.assertEqual(strip_task_number_prefix("1. Research"), "Research")
        self.assertEqual(strip_task_number_prefix("2) Design"), "Design")
        self.assertEqual(strip_task_number_prefix("3 - Launch"), "Launch")

    def test_progress_tracking_module_is_import_safe(self):
        module_path = Path(__file__).resolve().parent / "progress_tracking.py"
        spec = importlib.util.spec_from_file_location("progress_tracking_temp", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertTrue(hasattr(module, "plan"))
        self.assertEqual(module.plan.Clients_progress, {})

    def test_language_switch_supports_english_and_arabic(self):
        self.assertEqual(T("Client Details"), "Client Details")
        set_language("ar")
        self.assertEqual(T("Client Details"), "تفاصيل العميل")
        set_language("eng")
        self.assertEqual(T("Client Details"), "Client Details")

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

    def test_log_output_dir_defaults_to_application_package_folders(self):
        for folder_name in ["clients_logs", "tasks_logs", "observation_logs"]:
            output_dir = resolve_log_output_dir(folder_name)
            self.assertTrue(output_dir.exists())
            self.assertIn("application_outputs", str(output_dir))
            self.assertTrue(output_dir.name == folder_name or output_dir.parts[-2] == "application_outputs")

    def test_progress_app_exposes_separate_export_actions(self):
        self.assertTrue(hasattr(ProgressApp, "export_client_log"))
        self.assertTrue(hasattr(ProgressApp, "export_task_log"))
        self.assertTrue(hasattr(ProgressApp, "export_observation_log"))

    def test_task_listboxes_include_horizontal_scrollbars(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertGreaterEqual(source.count("xscrollcommand="), 2)
        self.assertGreaterEqual(source.count("orient=\"horizontal\""), 2)

    def test_contract_details_task_button_and_window_fields_are_present(self):
        self.assertTrue(hasattr(ProgressApp, "open_contract_details_window"))

        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("Contract Details", source)
        self.assertIn("Contract Number", source)
        self.assertIn("Commercial Registration Number", source)
        self.assertIn("Authorized Signature Name", source)
        self.assertIn("Open Issues Requiring Attention", source)

    def test_contract_details_are_saved_with_client_record(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Ali", "123456", "Retail")

        saved = manager.clients[0].contract_details = {
            "contract_number": "CN-001",
            "starting_date": "2026-01-01",
            "ending_date": "2027-01-01",
            "commercial_registration_number": "CR-123",
            "authorized_signature_name": "Samir",
            "rent_value": "1500",
            "currency_type": "OMR",
            "open_issues": "Need legal review",
        }
        manager.save_clients()

        reloaded = ClientManager(self.file_path)
        self.assertEqual(reloaded.clients[0].contract_details["contract_number"], "CN-001")
        self.assertEqual(reloaded.clients[0].contract_details["authorized_signature_name"], "Samir")
        self.assertEqual(reloaded.clients[0].contract_details["currency_type"], "OMR")
        self.assertIn("Need legal review", reloaded.clients[0].contract_details["open_issues"])

    def test_contract_details_include_default_oman_currency_selection(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("currency_type", source)
        self.assertIn("OMR", source)
        self.assertIn("Currency Type", source)

    def test_package_app_backfills_missing_currency_type_from_legacy_client_records(self):
        import package_app

        legacy_records = [{
            "name": "Legacy Client",
            "contact": "+96890000000",
            "business": "Retail",
            "contract_details": {
                "contract_number": "CN-100",
                "rent_value": "250",
            },
        }]

        migrated = package_app.normalize_legacy_client_data(legacy_records)
        self.assertEqual(migrated[0]["contract_details"]["currency_type"], "OMR")

    def test_emoji_font_families_include_windows_emoji_support(self):
        families = get_emoji_font_families()
        self.assertIn("Segoe UI Emoji", families)
        self.assertIn("Segoe UI Symbol", families)

    def test_package_metadata_matches_current_clients_manager_app(self):
        try:
            from package_app import APP_DISPLAY_NAME, resolve_target_icon
        except ImportError:
            self.fail("package_app is not importable from the project root")

        self.assertEqual(APP_DISPLAY_NAME, "Clients Manager")
        icon_path = resolve_target_icon()
        self.assertTrue(icon_path.exists())
        self.assertIn("starco_icon.ico", icon_path.name)


if __name__ == "__main__":
    unittest.main()
