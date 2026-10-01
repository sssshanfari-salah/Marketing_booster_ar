import importlib.util
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock
from tkinter import ttk

import arabic_reshaper
from bidi.algorithm import get_display

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_code.logic.clients_management import (
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
from python_code.ui.dashboard import (
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
from python_code.logic.sync_documents import TARGET

try:
    from package_app import resolve_desktop_dir
except ImportError:
    resolve_desktop_dir = None


class WelcomeAccessTests(unittest.TestCase):
    def test_translation_helpers_are_exposed(self):
        from python_code.ui import dashboard as ui
        self.assertTrue(callable(ui.T))
        self.assertTrue(callable(ui.set_language))
        self.assertEqual(ui.T("Guest"), "Guest")
        self.assertEqual(ui.set_language("ar"), "ar")
        self.assertEqual(ui.T("Guest"), "ضيف")
        self.assertEqual(ui.set_language("eng"), "eng")

    def test_successful_welcome_login_updates_status_without_opening_overview(self):
        from python_code.ui import dashboard as ui

        class DummyVar:
            def __init__(self, value=""):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        dummy = type("DummyWelcome", (), {
            "user_name_var": DummyVar("Alice"),
            "user_email_var": DummyVar("alice@example.com"),
            "login_status_var": DummyVar(""),
            "destroy": lambda self: None,
            "guest_mode": False,
            "_refresh_login_status": lambda self: getattr(self, "login_status_var").set(f"Logged in as: {self.user_name_var.get()}") if getattr(self, "user_name_var").get() else None,
        })()

        with mock.patch.object(ui, "verify_registered_user", return_value=True), \
             mock.patch.object(ui, "save_user_profile"), \
             mock.patch.object(ui, "set_current_session_profile"), \
             mock.patch.object(ui, "messagebox") as mock_msgbox, \
             mock.patch.object(ui, "open_overview_window") as mock_open_overview:
            ui.WelcomeWindow.login_user(dummy)

        mock_msgbox.showinfo.assert_called_once()
        self.assertEqual(dummy.login_status_var.get(), "Logged in as: Alice")
        mock_open_overview.assert_not_called()

    def test_successful_relogin_keeps_welcome_open_and_updates_status(self):
        from python_code.ui import dashboard as ui

        class DummyVar:
            def __init__(self, value=""):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        dummy = type("DummyWelcome", (), {
            "user_name_var": DummyVar("Alice"),
            "user_email_var": DummyVar("alice@example.com"),
            "login_status_var": DummyVar(""),
            "destroy": lambda self: None,
            "guest_mode": False,
            "_refresh_login_status": lambda self: getattr(self, "login_status_var").set(f"Logged in as: {self.user_name_var.get()}") if getattr(self, "user_name_var").get() else None,
        })()

        with mock.patch.object(ui, "verify_registered_user", return_value=True), \
             mock.patch.object(ui, "save_user_profile"), \
             mock.patch.object(ui, "set_current_session_profile"), \
             mock.patch.object(ui, "messagebox"), \
             mock.patch.object(ui, "open_overview_window") as mock_open_overview:
            ui.WelcomeWindow.login_user(dummy)
            ui.WelcomeWindow.login_user(dummy)

        self.assertEqual(mock_open_overview.call_count, 0)
        self.assertEqual(dummy.login_status_var.get(), "Logged in as: Alice")

    def test_overview_button_is_enabled_for_all_welcome_users(self):
        original_profile = getattr(__import__("python_code.ui.dashboard", fromlist=["CURRENT_SESSION_PROFILE"]), "CURRENT_SESSION_PROFILE").copy()
        try:
            for profile in (
                {"name": "Guest", "email": "Guest"},
                {"name": "", "email": ""},
                {"name": "Salah", "email": "sssshanfari@gmail.com"},
            ):
                from python_code.ui import dashboard as ui
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
                self.assertEqual(dummy.overview_button.state, "normal")
                self.assertEqual(dummy.contract_button.state, "disabled" if not ui.is_registered_user_profile(profile) else "normal")
        finally:
            from python_code.ui import dashboard as ui
            ui.CURRENT_SESSION_PROFILE = original_profile.copy()

    def test_default_session_starts_as_guest(self):
        from python_code.ui import dashboard as ui

        original = ui.CURRENT_SESSION_PROFILE.copy()
        try:
            ui.sync_session_profile(clear=True)
            self.assertEqual(ui.ensure_default_guest_session(), {"name": "Guest", "email": "Guest"})
            self.assertTrue(ui.is_guest_profile(ui.CURRENT_SESSION_PROFILE))
        finally:
            ui.CURRENT_SESSION_PROFILE = original

    def test_closing_registration_window_keeps_previous_user(self):
        from python_code.ui import dashboard as ui

        class DummyVar:
            def __init__(self, value=""):
                self.value = value
            def get(self):
                return self.value
            def set(self, value):
                self.value = value

        dummy = type("DummyWelcome", (), {
            "user_name_var": DummyVar("Alice"),
            "user_email_var": DummyVar("alice@example.com"),
            "login_status_var": DummyVar(""),
            "_refresh_login_status": lambda self: self.login_status_var.set(f"Logged in as: {self.user_name_var.get()}"),
            "guest_mode": False,
        })()

        with mock.patch.object(ui, "UserRegistrationWindow") as mock_registration, \
             mock.patch.object(ui, "load_user_profile", return_value={"name": "Salah", "email": "salah@example.com"}):
            instance = mock_registration.return_value
            instance.grab_set.return_value = None
            instance.wait_window.return_value = None
            ui.WelcomeWindow.open_registration_window(dummy)

        self.assertEqual(dummy.user_name_var.get(), "Alice")
        self.assertEqual(dummy.user_email_var.get(), "alice@example.com")
        self.assertEqual(dummy.login_status_var.get(), "Logged in as: Alice")

    def test_register_user_updates_active_session_profile(self):
        from python_code.ui import dashboard as ui

        class DummyVar:
            def __init__(self, value=""):
                self.value = value
            def get(self):
                return self.value
            def set(self, value):
                self.value = value

        master = type("DummyMaster", (), {
            "user_name_var": DummyVar(""),
            "user_email_var": DummyVar(""),
            "_refresh_login_status": lambda self: None,
        })()

        registration = object.__new__(ui.UserRegistrationWindow)
        registration.master = master
        registration.user_name_var = DummyVar("Alice")
        registration.user_email_var = DummyVar("alice@example.com")
        registration.destroy = lambda: None
        registration.focus_set = lambda: None
        registration.registration_status_var = DummyVar("")

        with mock.patch.object(ui, "user_registeration", return_value={"name": "Alice", "email": "alice@example.com"}), \
             mock.patch.object(ui, "set_current_session_profile") as mock_set_profile, \
             mock.patch.object(ui, "messagebox") as mock_msgbox:
            ui.UserRegistrationWindow.register_user(registration)

        mock_set_profile.assert_called_once_with(user_name="Alice", user_email="alice@example.com")
        mock_msgbox.showinfo.assert_called_once()

    def test_reopening_welcome_refreshes_login_state(self):
        from python_code.ui import dashboard as ui

        welcome_window = mock.Mock()
        welcome_window.winfo_exists.return_value = True
        welcome_window._refresh_login_status = mock.Mock()

        ui._ACTIVE_WELCOME_WINDOW = welcome_window
        ui._ACTIVE_PROGRESS_APP = mock.Mock()

        ui.open_welcome_home(force_new=False)

        welcome_window._refresh_login_status.assert_called_once()
        welcome_window.deiconify.assert_called_once()
        welcome_window.lift.assert_called_once()
        welcome_window.focus_set.assert_called_once()

    def test_switching_between_welcome_and_overview_closes_the_other_window(self):
        from python_code.ui import dashboard as ui

        welcome_window = mock.Mock()
        overview_window = mock.Mock()
        welcome_window.winfo_exists.return_value = True
        overview_window.winfo_exists.return_value = True

        ui._ACTIVE_WELCOME_WINDOW = welcome_window
        ui._ACTIVE_PROGRESS_APP = overview_window

        ui.open_overview_window(force_new=True)

        welcome_window.destroy.assert_called_once()
        self.assertIsNone(ui._ACTIVE_WELCOME_WINDOW)
        self.assertIsNotNone(ui._ACTIVE_PROGRESS_APP)

        new_welcome = mock.Mock()
        new_welcome.winfo_exists.return_value = True
        with mock.patch.object(ui, "WelcomeWindow", return_value=new_welcome):
            ui.open_welcome_home(force_new=True)

        overview_window.destroy.assert_called_once()
        self.assertIsNone(ui._ACTIVE_PROGRESS_APP)
        self.assertIsNotNone(ui._ACTIVE_WELCOME_WINDOW)


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
        original_provider = __import__("python_code.ui.dashboard", fromlist=["get_emoji_font_families"]).get_emoji_font_families
        try:
            from python_code.ui import dashboard as ui
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
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertGreaterEqual(source.count("xscrollcommand="), 2)
        self.assertGreaterEqual(source.count("orient=\"horizontal\""), 2)

    def test_contract_details_task_button_and_window_fields_are_present(self):
        self.assertTrue(hasattr(ProgressApp, "open_contract_details_window"))

        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
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
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("self.client_selector_var", source)
        self.assertIn("<<ComboboxSelected>>", source)
        self.assertIn("self._switch_client_for_transactions", source)

    def test_transaction_status_uses_checkbox_and_completion_popup(self):
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("Checkbutton", source)
        self.assertIn("showinfo", source)
        self.assertIn("Payment completed", source)
        self.assertIn("Bank Transaction", source)
        self.assertIn("Cheque", source)
        self.assertIn("state=\"disabled\"", source)

    def test_transaction_completion_popup_requires_valid_saved_row(self):
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
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
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _get_previous_month", source)
        self.assertIn("previous_month = self.month_options[current_index - 1]", source)
        self.assertIn("Outstanding payment", source)

    def test_payment_follow_up_actions_are_generated_from_pending_months(self):
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _build_payment_follow_up_tasks", source)
        self.assertIn("Follow up payment", source)
        self.assertIn("self.plan.pending_tasks", source)

    def test_due_date_matches_selected_month(self):
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _coerce_due_date_for_month", source)
        self.assertIn("calendar.monthrange", source)
        self.assertIn("normalized = self._coerce_due_date_for_month", source)

    def test_transaction_row_edits_and_payment_preview_are_available(self):
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _update_amount", source)
        self.assertIn("def _update_due_date", source)
        self.assertIn("def _update_bank_name", source)
        self.assertIn("ClientLogPreviewWindow", source)
        self.assertIn("text_widget.insert(\"1.0\", self.build_report_text())", source)

    def test_transaction_due_date_picker_and_next_month_logic_are_present(self):
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
        with source_path.open("r", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("def _pick_due_date", source)
        self.assertIn("def _next_month_for_new_row", source)
        self.assertIn("self._next_month_for_new_row()", source)
        self.assertIn("if self.month_options[-1] in existing_months:", source)

    def test_payment_report_includes_contract_period_and_transaction_details(self):
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
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
        source_path = Path(__file__).resolve().parent / "ui" / "dashboard.py"
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

    def test_package_app_handles_blank_legacy_currency_aliases(self):
        import package_app

        legacy_records = [{
            "name": "Legacy Client",
            "contact": "+96890000000",
            "business": "Retail",
            "contractDetails": {
                "contract_number": "CN-200",
                "rent_value": "420",
                "currency_type": "",
            },
        }]

        migrated = package_app.normalize_legacy_client_data(legacy_records)
        self.assertEqual(migrated[0]["contract_details"]["currency_type"], "OMR")
        self.assertEqual(migrated[0]["contract_details"]["contract_number"], "CN-200")

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
        module_path = Path(__file__).resolve().parent / "ui" / "reservation_contract.py"
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
        module_path = Path(__file__).resolve().parent / "ui" / "reservation_contract.py"
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
        module_path = Path(__file__).resolve().parent / "ui" / "reservation_contract.py"
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

    def test_reservation_status_button_opens_contract_form_instead_of_popup(self):
        from python_code.ui import dashboard as ui

        dummy = object.__new__(ui.ProgressApp)
        dummy.client_name_var = type("DummyVar", (), {"get": lambda self: "Ali"})()
        dummy.contact_var = type("DummyVar", (), {"get": lambda self: "+96891234567"})()
        dummy.shop_number_var = type("DummyVar", (), {"get": lambda self: "12"})()
        dummy.electrical_meter_var = type("DummyVar", (), {"get": lambda self: "28609687"})()

        with mock.patch.object(ui, "ShopReservationForm") as mock_form, \
             mock.patch.object(ui, "is_registered_user_profile", return_value=True), \
             mock.patch.object(ui, "is_guest_profile", return_value=False), \
             mock.patch.object(ui, "CURRENT_SESSION_PROFILE", {"name": "Salah", "email": "salah@example.com"}):
            ui.ProgressApp.open_reservation_status_window(dummy)

        mock_form.assert_called_once_with(client_name="Ali")

    def test_contract_form_prefills_client_details_and_auto_syncs_shop_meter(self):
        module_path = Path(__file__).resolve().parent / "ui" / "reservation_contract.py"
        spec = importlib.util.spec_from_file_location("ui_reservation_contract_module_prefill", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        form = object.__new__(module.ShopReservationForm)
        form.saved_client_data = {
            "name": "Ali",
            "contact": "+96891234567",
            "business": "Retail",
            "email": "ali@example.com",
            "address": "Muscat",
            "shop_number": "12",
            "electrical_meter": "28609687",
        }
        form.client_name = "Ali"
        form.main_vars = {
            "lessor": tk.StringVar(),
            "lessor contact": tk.StringVar(),
            "lessee": tk.StringVar(),
            "lessee contact": tk.StringVar(),
            "date": tk.StringVar(),
            "duration": tk.StringVar(),
            "business": tk.StringVar(),
            "email": tk.StringVar(),
            "address": tk.StringVar(),
        }
        form.renew_var = tk.StringVar(value="Yes")
        form.shop_var = tk.StringVar()
        form.elec_var = tk.StringVar()
        form.payment_vars = {"rent": tk.StringVar(), "deposit": tk.StringVar(), "bank": tk.StringVar(), "holder": tk.StringVar()}

        form.prefill_from_saved_client()

        self.assertEqual(form.main_vars["lessor"].get(), "Ali")
        self.assertEqual(form.main_vars["lessor contact"].get(), "+96891234567")
        self.assertEqual(form.main_vars["business"].get(), "Retail")
        self.assertEqual(form.main_vars["email"].get(), "ali@example.com")
        self.assertEqual(form.main_vars["address"].get(), "Muscat")
        self.assertEqual(form.shop_var.get(), "12")
        self.assertEqual(form.elec_var.get(), "28609687")


if __name__ == "__main__":
    unittest.main()
