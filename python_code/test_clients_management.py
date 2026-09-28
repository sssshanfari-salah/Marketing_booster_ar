import importlib.util
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk

import arabic_reshaper
from bidi.algorithm import get_display

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clients_management import (
    Client,
    ClientManager,
    build_clients_report_text,
    format_contact_number,
    generate_contract_months,
    normalize_contract_details,
    normalize_duration_value,
    normalize_reservation_status,
    normalize_shop_value,
)
from clients_progress_ui import (
    Plan,
    ProgressApp,
    T,
    WelcomeWindow,
    apply_bidi_text,
    build_review_log_report_text,
    build_task_log_report_text,
    get_emoji_font_families,
    load_shop_electrical_meter_map,
    parse_task_items,
    refresh_translatable_widget,
    resolve_log_output_dir,
    set_emoji_translated_label,
    set_language,
    strip_task_number_prefix,
    validate_translation_coverage,
)
from sync_documents import TARGET

try:
    from package_app import resolve_desktop_dir
except ImportError:
    resolve_desktop_dir = None


class WelcomeAccessTests(unittest.TestCase):
    def test_overview_button_is_enabled_only_after_login(self):
        original_profile = getattr(__import__("clients_progress_ui", fromlist=["CURRENT_SESSION_PROFILE"]), "CURRENT_SESSION_PROFILE").copy()
        try:
            for profile, expected_overview_state in (
                ({"name": "Guest", "email": "Guest"}, "disabled"),
                ({"name": "", "email": ""}, "disabled"),
                ({"name": "Salah", "email": "sssshanfari@gmail.com"}, "normal"),
            ):
                import clients_progress_ui as ui
                ui.CURRENT_SESSION_PROFILE = profile.copy()

                class FakeWidget:
                    def __init__(self):
                        self.state = "disabled"

                    def configure(self, **kwargs):
                        self.state = kwargs.get("state", self.state)

                    def winfo_exists(self):
                        return True

                class DummyWindow:
                    def __init__(self):
                        self.overview_button = FakeWidget()
                        self.contract_button = FakeWidget()

                    def winfo_exists(self):
                        return True

                dummy = DummyWindow()
                WelcomeWindow._sync_overview_access(dummy)
                self.assertEqual(dummy.overview_button.state, expected_overview_state)
                self.assertEqual(dummy.contract_button.state, "disabled")
        finally:
            import clients_progress_ui as ui
            ui.CURRENT_SESSION_PROFILE = original_profile.copy()


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

    def test_client_directory_uses_client_name_and_shop_number(self):
        manager = ClientManager(self.file_path)
        result = manager.add_client("Alpha Test", "5551234", "Retail", "alpha@example.com", shop_number="12")

        self.assertTrue(result)
        expected_dir = Path(self.file_path).parent / "Clients" / "Alpha_Test_12"
        self.assertTrue(expected_dir.exists())
        self.assertEqual(manager.clients[0].shop_number, "12")

    def test_client_address_and_electrical_meter_are_persisted(self):
        client = Client(
            "Nora",
            "5551234",
            "Consulting",
            "nora@example.com",
            "12",
            address="Main Street, Muscat",
            electrical_meter="EM-2048",
            notes="Follow-up with landlord",
        )

        payload = client.to_dict()
        self.assertEqual(payload["address"], "Main Street, Muscat")
        self.assertEqual(payload["electrical_meter"], "EM-2048")
        self.assertEqual(payload["notes"], "Follow-up with landlord")

        rebuilt = Client.from_dict(payload)
        self.assertEqual(rebuilt.address, "Main Street, Muscat")
        self.assertEqual(rebuilt.electrical_meter, "EM-2048")
        self.assertEqual(rebuilt.notes, "Follow-up with landlord")

    def test_shop_number_lookup_fills_electrical_meter(self):
        meters = load_shop_electrical_meter_map()
        self.assertIn("12", meters)
        self.assertEqual(meters["12"], "28609687")
        self.assertEqual(meters["Office"], "28609686")

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

    def test_contract_months_are_generated_from_contract_dates(self):
        months = generate_contract_months("2026-01-15", "2026-03-10")

        self.assertEqual(months[0], "2026-01")
        self.assertEqual(months[-1], "2026-03")
        self.assertIn("2026-02", months)

    def test_duration_fields_are_normalized_consistently(self):
        contract = normalize_contract_details({"duration_years": "3 Years"})
        self.assertEqual(contract["duration_years"], "3")

        status = normalize_reservation_status({"contract_duration": "5 years"})
        self.assertEqual(status["contract_duration"], "5")

        self.assertEqual(normalize_duration_value("2.5 Years"), "2.5")

    def test_multiple_shop_numbers_are_kept_in_order(self):
        self.assertEqual(normalize_shop_value(["12", "14", "16"]), "12, 14, 16")
        self.assertEqual(normalize_shop_value(("12", "14")), "12, 14")
        self.assertEqual(normalize_shop_value("12"), "12")

    def test_available_shop_numbers_exclude_used_ones(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Ali", "123", "Retail", shop_number="1")
        manager.add_client("Sara", "456", "Boutique", shop_number="3")

        available = manager.get_available_shop_numbers()
        self.assertIn("2", available)
        self.assertIn("4", available)
        self.assertNotIn("1", available)
        self.assertNotIn("3", available)

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

    def test_task_and_review_log_reports_include_preview_text(self):
        plan = Plan(Client("Ali", "123456", "Stationery"), all_tasks=["Call client", "Send invoice"])

        task_report = build_task_log_report_text(plan)
        self.assertIn("Task log", task_report)
        self.assertIn("Ali", task_report)
        self.assertIn("Call client", task_report)
        self.assertIn("Progress:", task_report)

        review_report = build_review_log_report_text("Ali", "Positive follow-up")
        self.assertIn("Review log", review_report)
        self.assertIn("Ali", review_report)
        self.assertIn("Positive follow-up", review_report)

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

    def test_apply_bidi_only_to_pure_arabic_labels(self):
        pure_arabic = "العنوان"
        mixed_text = "Address العنوان"
        self.assertEqual(apply_bidi_text(pure_arabic), arabic_reshaper.reshape(pure_arabic))
        self.assertEqual(apply_bidi_text(mixed_text), mixed_text)

        emoji_prefixed_label = "👤 اسم العميل"
        expected_emoji_label = f"👤 {arabic_reshaper.reshape('اسم العميل')}"
        self.assertEqual(apply_bidi_text(emoji_prefixed_label), expected_emoji_label)

        self.assertEqual(T("Address"), "Address")
        set_language("ar")
        self.assertEqual(T("Address"), "العنوان")
        self.assertEqual(T("Client Details"), "تفاصيل العميل")
        self.assertEqual(T("Client: {client_name}"), "العميل: {client_name}")
        set_language("eng")

    def test_language_switch_supports_english_and_arabic(self):
        self.assertEqual(T("Client Details"), "Client Details")
        set_language("ar")
        self.assertEqual(T("Client Details"), "تفاصيل العميل")
        self.assertEqual(T("Address"), "العنوان")
        self.assertEqual(T("Electrical Meter"), "عداد الكهرباء")
        set_language("eng")
        self.assertEqual(T("Client Details"), "Client Details")
        self.assertEqual(T("Address"), "Address")
        self.assertEqual(T("Electrical Meter"), "Electrical Meter")

    def test_client_details_frame_emoji_only_in_english(self):
        root = tk.Tk()
        root.withdraw()
        try:
            frame = ttk.LabelFrame(root, text="Client Details")
            set_language("eng")
            set_emoji_translated_label(frame, "Client Details", "📋 ")
            self.assertTrue(frame.cget("text").startswith("📋"))

            set_language("ar")
            set_emoji_translated_label(frame, "Client Details", "📋 ")
            self.assertFalse(frame.cget("text").startswith("📋"))
            self.assertIn("تفاصيل", frame.cget("text"))
        finally:
            root.destroy()
            set_language("eng")

    def test_refresh_translatable_widget_does_not_force_emoji_font_for_plain_arabic_labels(self):
        original_provider = __import__("python_code.clients_progress_ui", fromlist=["get_emoji_font_families"]).get_emoji_font_families
        try:
            from python_code import clients_progress_ui as ui
            ui.get_emoji_font_families = lambda: ["Noto Color Emoji"]

            root = tk.Tk()
            root.withdraw()
            label = ttk.Label(root, text="Client Name")
            initial_font = label.cget("font")
            set_language("ar")
            ui.refresh_translatable_widget(label, "Client Name")
            self.assertEqual(label.cget("font"), initial_font)
            self.assertIn("اسم", label.cget("text"))
            root.destroy()
        finally:
            ui.get_emoji_font_families = original_provider
            set_language("eng")

    def test_resolve_desktop_dir_uses_existing_windows_desktop(self):
        if resolve_desktop_dir is None:
            self.fail("resolve_desktop_dir is not available")

        desktop_dir = resolve_desktop_dir()
        self.assertTrue(desktop_dir.exists())
        self.assertTrue(str(desktop_dir).endswith("Desktop") or str(desktop_dir).endswith("Desktop") or "Desktop" in str(desktop_dir))

    def test_sync_documents_target_uses_current_project_root(self):
        project_root = Path(__file__).resolve().parent.parent
        expected_target = project_root / "python_code" / "docs" / "documents.txt"
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

    def test_arabic_translations_cover_all_ui_labels(self):
        self.assertIsNone(validate_translation_coverage())

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

    def test_client_transactions_are_persisted_and_available_in_ui(self):
        self.assertTrue(hasattr(ProgressApp, "open_transactions_window"))

        manager = ClientManager(self.file_path)
        manager.add_client("Ali", "123456", "Retail")
        manager.clients[0].transactions = [{
            "month": "2026-09",
            "status": "Paid",
            "amount": "250",
            "payment_method": "Cheque",
            "cheque_number": "CH-204",
            "due_date": "2026-09-30",
            "bank_name": "Bank Muscat",
        }]
        manager.save_clients()

        reloaded = ClientManager(self.file_path)
        self.assertEqual(reloaded.clients[0].transactions[0]["month"], "2026-09")
        self.assertEqual(reloaded.clients[0].transactions[0]["cheque_number"], "CH-204")
        self.assertEqual(reloaded.clients[0].transactions[0]["bank_name"], "Bank Muscat")

    def test_transaction_window_has_client_selector_dropdown(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("self.client_selector_var", source)
        self.assertIn("<<ComboboxSelected>>", source)
        self.assertIn("self._switch_client_for_transactions", source)

    def test_transaction_status_uses_checkbox_and_completion_popup(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("Checkbutton", source)
        self.assertIn("showinfo", source)
        self.assertIn("Payment completed", source)
        self.assertIn("Bank Transaction", source)
        self.assertIn("Cheque", source)
        self.assertIn("state=\"disabled\"", source)

    def test_transaction_completion_popup_requires_valid_saved_row(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _can_complete_payment", source)
        self.assertIn("if not completed:", source)
        self.assertIn("entry[\"status\"] = \"Pending\"", source)
        self.assertIn("return bool(cheque_number)", source)
        self.assertIn("return bool(bank_detail)", source)
        self.assertIn("save_transactions", source)
        self.assertIn("Payment completed", source)
        self.assertIn("showinfo", source)

    def test_previous_month_must_be_paid_before_next_month_completion(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _get_previous_month", source)
        self.assertIn("previous_month = self.month_options[current_index - 1]", source)
        self.assertIn("Outstanding payment", source)

    def test_payment_follow_up_actions_are_generated_from_pending_months(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _build_payment_follow_up_tasks", source)
        self.assertIn("Follow up payment", source)
        self.assertIn("self.plan.pending_tasks", source)

    def test_due_date_matches_selected_month(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _coerce_due_date_for_month", source)
        self.assertIn("calendar.monthrange", source)
        self.assertIn("normalized = self._coerce_due_date_for_month", source)

    def test_transaction_row_edits_and_payment_preview_are_available(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _update_amount", source)
        self.assertIn("def _update_due_date", source)
        self.assertIn("def _update_bank_name", source)
        self.assertIn("ClientLogPreviewWindow", source)
        self.assertIn("text_widget.insert(\"1.0\", self.build_report_text())", source)

    def test_transaction_due_date_picker_and_next_month_logic_are_present(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _pick_due_date", source)
        self.assertIn("def _next_month_for_new_row", source)
        self.assertIn("self._next_month_for_new_row()", source)
        self.assertIn("if self.month_options[-1] in existing_months:", source)

    def test_payment_report_includes_contract_period_and_transaction_details(self):
        source_path = Path(__file__).resolve().parent / "clients_progress_ui.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("build_client_payment_report_text", source)
        self.assertIn("Contract Period Status", source)
        self.assertIn("Bank Transaction Details", source)

    def test_package_app_keeps_latest_transaction_fields(self):
        source_path = Path(__file__).resolve().parent.parent / "package_app.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("bank_transaction_details", source)
        self.assertIn("normalize_payment_method", source)
        self.assertIn("Bank Transaction", source)

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

    def test_reservation_ui_module_integrates_with_project_app(self):
        module_path = Path(__file__).resolve().parent / "ui_reservation_contract.py"
        self.assertTrue(module_path.exists(), "Reservation UI module is missing or not named as a Python file.")

        spec = importlib.util.spec_from_file_location("ui_reservation_contract_module", module_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertTrue(hasattr(module, "ShopReservationForm"))
        self.assertTrue(hasattr(module, "main"))

    def test_reservation_status_is_normalized_and_persisted_with_client_record(self):
        manager = ClientManager(self.file_path)
        manager.add_client("Ali", "123456", "Retail")

        manager.clients[0].reservation_status = {
            "deposit_status": "Deposite recieved",
            "contract_status": "completed",
        }
        manager.save_clients()

        reloaded = ClientManager(self.file_path)
        self.assertEqual(reloaded.clients[0].reservation_status["deposit_status"], "Deposite recieved")
        self.assertEqual(reloaded.clients[0].reservation_status["contract_status"], "completed")

    def test_reservation_shop_validation_rejects_blank_numeric_and_duplicate_entries(self):
        module_path = Path(__file__).resolve().parent / "ui_reservation_contract.py"
        spec = importlib.util.spec_from_file_location("ui_reservation_contract_module_validation", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertFalse(module.ShopReservationForm.validate_shop_entry("", existing=[])[0])
        self.assertFalse(module.ShopReservationForm.validate_shop_entry("abc", existing=[])[0])
        self.assertFalse(module.ShopReservationForm.validate_shop_entry("5", existing=[("5", "123")])[0])
        self.assertTrue(module.ShopReservationForm.validate_shop_entry("12", existing=[("5", "123")])[0])

        valid, message = module.ShopReservationForm.validate_shop_entry("5", existing=[("5", "123")])
        self.assertFalse(valid)
        self.assertIn("already exists", message.lower())

    def test_reservation_preview_falls_back_when_mapped_contract_file_is_missing(self):
        module_path = Path(__file__).resolve().parent / "ui_reservation_contract.py"
        spec = importlib.util.spec_from_file_location("ui_reservation_contract_module_preview", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        temp_dir = tempfile.TemporaryDirectory()
        try:
            mapping_path = Path(temp_dir.name) / "reservation_contracts.json"
            stale_file = Path(temp_dir.name) / "contract_12.txt"
            mapping_path.write_text(json.dumps({"12": str(stale_file)}), encoding="utf-8")

            resolved = module.ShopReservationForm.resolve_contract_file(mapping_path, "12")
            self.assertIsNone(resolved)

            cleaned_payload = json.loads(mapping_path.read_text(encoding="utf-8"))
            self.assertNotIn("12", cleaned_payload)
        finally:
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
