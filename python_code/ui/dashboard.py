import calendar
import json
import os
import re
import subprocess
import sys
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from ui.utils import (
        apply_bidi_text,
        configure_emoji_label,
        get_emoji_font_families,
        is_arabic_text,
        refresh_translatable_widget,
        set_emoji_translated_label,
    )
except ImportError:  # pragma: no cover - script execution fallback
    from ui.utils import (
        apply_bidi_text,
        configure_emoji_label,
        get_emoji_font_families,
        is_arabic_text,
        refresh_translatable_widget,
        set_emoji_translated_label,
    )

try:
    import win32print
except ImportError:
    win32print = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from logic.clients_management import (
    Client,
    ClientManager,
    build_client_payment_report_text,
    build_clients_report_text,
    format_contact_number,
    generate_contract_months,
    resolve_clients_data_path,
)

APP_ICON = None
for candidate in [
    Path(sys._MEIPASS) / "starco_icon.ico" if getattr(sys, "_MEIPASS", None) else None,
    Path(__file__).resolve().parent.parent / "starco_icon.ico",
    Path(__file__).resolve().parent / "starco_icon.ico",
]:
    if candidate is not None and candidate.exists():
        APP_ICON = candidate
        break

if APP_ICON is None:
    APP_ICON = Path(__file__).resolve().parent.parent / "starco_icon.ico"

CURRENT_LANGUAGE = "eng"
APP_ROOT = Path(__file__).resolve().parent.parent

try:
    from .session import (
        APP_ROOT as SESSION_APP_ROOT,
        CURRENT_SESSION_PROFILE,
        GUESTS_FILE,
        LEGACY_USER_PROFILE_FILE,
        USERS_FILE,
        _normalize_guest_record,
        _normalize_user_record,
        _read_json_file,
        _write_json_file,
        append_report_footer,
        build_report_issuer_footer,
        ensure_default_guest_session,
        is_admin_registration_allowed,
        is_guest_login_credentials,
        is_guest_profile,
        is_registered_user_profile,
        is_registration_submission_allowed,
        load_guest_profiles,
        load_registered_users,
        load_user_profile,
        save_guest_profile,
        save_user_profile,
        set_current_session_profile,
        sync_session_profile,
        user_registeration,
        user_registration,
        verify_registered_user,
    )
except ImportError:  # pragma: no cover - script execution fallback
    from ui.session import (
        APP_ROOT as SESSION_APP_ROOT,
        CURRENT_SESSION_PROFILE,
        GUESTS_FILE,
        LEGACY_USER_PROFILE_FILE,
        USERS_FILE,
        _normalize_guest_record,
        _normalize_user_record,
        _read_json_file,
        _write_json_file,
        append_report_footer,
        build_report_issuer_footer,
        ensure_default_guest_session,
        is_admin_registration_allowed,
        is_guest_login_credentials,
        is_guest_profile,
        is_registered_user_profile,
        is_registration_submission_allowed,
        load_guest_profiles,
        load_registered_users,
        load_user_profile,
        save_guest_profile,
        save_user_profile,
        set_current_session_profile,
        sync_session_profile,
        user_registeration,
        user_registration,
        verify_registered_user,
    )

APP_ROOT = SESSION_APP_ROOT
COUNTRY_CODES_PATH = Path(__file__).resolve().parent / "country_codes.json"




def build_all_clients_row_values(client, progress_info=None):
    if progress_info is None:
        progress_info = {}

    progress = progress_info.get("progress", 0)
    pending_tasks = progress_info.get("pending_tasks", [])
    all_tasks = progress_info.get("all_tasks", [])

    reservation = getattr(client, "reservation_status", {}) or {}
    contract_status = str(reservation.get("contract_status", "") or "").strip().lower()
    if contract_status in {"completed", "complete", "done"}:
        reservation_status = "Completed"
    elif contract_status == "under progress":
        reservation_status = "Under progress"
    else:
        reservation_status = "Not reserved"

    return (
        client.name,
        getattr(client, "contact", ""),
        client.business,
        getattr(client, "shop_number", ""),
        getattr(client, "electrical_meter", getattr(client, "notes", "")),
        reservation_status,
        f"{progress}%",
        f"{len(pending_tasks)} / {len(all_tasks)}",
    )


def resolve_log_output_dir(log_type="general"):
    root_dir = Path(__file__).resolve().parent.parent
    if getattr(sys, "_MEIPASS", None):
        root_dir = Path(sys._MEIPASS)

    output_root = root_dir / "application_outputs"
    target_dir = output_root / str(log_type).strip().strip("/") if str(log_type).strip() else output_root
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def load_shop_electrical_meter_map():
    try:
        from logic.shops_conversion_to_dic import shop_meter_map as shared_shop_meter_map
        return dict(shared_shop_meter_map)
    except Exception:
        return {}


def resolve_shop_electrical_meter(shop_number):
    shop_value = str(shop_number or "").strip()
    if not shop_value:
        return ""

    mapping = load_shop_electrical_meter_map()
    if shop_value in mapping:
        return str(mapping[shop_value]).strip()

    normalized = shop_value.lower()
    if normalized == "office":
        return str(mapping.get("Office", "")).strip()

    try:
        shop_id = int(shop_value)
    except ValueError:
        return ""

    if 1 <= shop_id <= 36:
        return str(mapping.get(str(shop_id), "")).strip()
    return ""


def _coerce_currency_amount(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0

    normalized = text.replace(",", "").replace("OMR", "").replace("omr", "")
    normalized = re.sub(r"[^0-9.\-]", "", normalized)
    if not normalized or normalized in {"-", "."}:
        return 0.0

    try:
        return float(normalized)
    except ValueError:
        return 0.0


def calculate_total_saved_client_rent(clients=None):
    if clients is None:
        manager = ClientManager(resolve_clients_data_path())
        manager.load_clients()
        clients = manager.clients

    total = 0.0
    for client in clients:
        if client is None:
            continue

        rent_value = ""
        contract_details = getattr(client, "contract_details", {})
        if isinstance(contract_details, dict):
            for key in ("rent_value", "monthly_rent", "rent"):
                value = contract_details.get(key)
                if value not in (None, ""):
                    rent_value = str(value)
                    break

        if not rent_value and isinstance(getattr(client, "reservation_status", None), dict):
            for key in ("rent_value", "monthly_rent", "rent"):
                value = client.reservation_status.get(key)
                if value not in (None, ""):
                    rent_value = str(value)
                    break

        total += _coerce_currency_amount(rent_value)

    return total


def calculate_remaining_shop_count(used_shop_numbers=None):
    if used_shop_numbers is None:
        manager = ClientManager(resolve_clients_data_path())
        manager.load_clients()
        used_shop_numbers = {str(getattr(client, "shop_number", "") or "").strip() for client in manager.clients}

    reserved = set()
    for value in used_shop_numbers or []:
        shop_number = str(value or "").strip()
        if shop_number:
            reserved.add(shop_number)

    return sum(1 for shop_number in range(1, 37) if str(shop_number) not in reserved)


def calculate_remaining_shop_rent(used_shop_numbers=None, per_shop_rent=0.0):
    return calculate_remaining_shop_count(used_shop_numbers) * _coerce_currency_amount(per_shop_rent)


def load_country_codes():
    fallback = [
        {"country": "Oman", "code": "+968"},
        {"country": "Saudi Arabia", "code": "+966"},
        {"country": "United Arab Emirates", "code": "+971"},
        {"country": "Qatar", "code": "+974"},
        {"country": "Kuwait", "code": "+965"},
        {"country": "Bahrain", "code": "+973"},
        {"country": "Jordan", "code": "+962"},
        {"country": "Egypt", "code": "+20"},
        {"country": "United States", "code": "+1"},
        {"country": "United Kingdom", "code": "+44"},
        {"country": "Germany", "code": "+49"},
        {"country": "France", "code": "+33"},
    ]

    if COUNTRY_CODES_PATH.exists():
        try:
            with COUNTRY_CODES_PATH.open("r", encoding="utf-8") as infile:
                data = json.load(infile)
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    return fallback


# Central UI constants and helper data used by the forms, translations, and client records.
COUNTRY_CODES = load_country_codes()
COUNTRY_OPTIONS = [item["country"] for item in COUNTRY_CODES]
COUNTRY_CODE_BY_NAME = {item["country"]: item["code"] for item in COUNTRY_CODES}
DEFAULT_COUNTRY = "Oman"
DEFAULT_COUNTRY_CODE = "+968"


# Convert a raw country code into a consistent international format like +968.
def normalize_country_code(code):
    if code is None:
        return DEFAULT_COUNTRY_CODE
    cleaned = str(code).strip()
    if not cleaned:
        return DEFAULT_COUNTRY_CODE
    return cleaned if cleaned.startswith("+") else f"+{cleaned}"


def format_task_entry(task, number=None):
    text = str(task).strip()
    if number is not None:
        return f"{number}. {text}" if text else f"{number}."
    return text if text else ""


def strip_task_number_prefix(task):
    text = str(task or "").strip()
    if not text:
        return ""

    cleaned = re.sub(r"^\s*\d+\s*(?:[\.)\-:\]|]|\-\s*)\s*", "", text)
    return cleaned.strip()


def validate_contact_number(new_value):
    return new_value == "" or new_value.isdigit()


def parse_contact_for_ui(contact_value):
    raw = str(contact_value or "").strip()
    if not raw:
        return "", DEFAULT_COUNTRY

    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return "", DEFAULT_COUNTRY

    for item in COUNTRY_CODES:
        country_code = item["code"].lstrip("+")
        if digits.startswith(country_code):
            local_number = digits[len(country_code):]
            return local_number.lstrip("0") if local_number else "", item["country"]

    if digits.startswith("968"):
        local_number = digits[3:]
        return local_number.lstrip("0") if local_number else "", "Oman"

    if digits.startswith("0"):
        return digits[1:], "Oman"

    return digits, DEFAULT_COUNTRY


# Pop-up calendar used when the user picks a date in contract or payment forms.
class DatePickerPopup(tk.Toplevel):
    def __init__(self, master=None, initial_value=""):
        super().__init__(master)
        self.title(T("Select Date"))
        self.transient(master)
        self.grab_set()
        self.result = ""

        self.current_year = datetime.today().year
        self.current_month = datetime.today().month
        if initial_value:
            parsed = False
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y %H:%M:%S"):
                try:
                    initial_dt = datetime.strptime(initial_value, fmt)
                    self.current_year = initial_dt.year
                    self.current_month = initial_dt.month
                    parsed = True
                    break
                except ValueError:
                    continue
            if not parsed:
                try:
                    initial_dt = datetime.fromisoformat(initial_value)
                    self.current_year = initial_dt.year
                    self.current_month = initial_dt.month
                except ValueError:
                    pass

        self.month_label = ttk.Label(self, text="")
        self.month_label.grid(row=0, column=1, sticky="ew", padx=6, pady=(8, 4))

        prev_month = ttk.Button(self, text="<", command=self.prev_month)
        prev_month.grid(row=0, column=0, padx=(8, 4), pady=(8, 4))
        next_month = ttk.Button(self, text=">", command=self.next_month)
        next_month.grid(row=0, column=2, padx=(4, 8), pady=(8, 4))

        weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for index, day in enumerate(weekdays):
            ttk.Label(self, text=day).grid(row=1, column=index, padx=3, pady=2)

        self.day_buttons = []
        for row in range(2, 8):
            for col in range(7):
                btn = ttk.Button(self, text="", width=4, command=lambda row=row, col=col: self._select_day(row, col))
                btn.grid(row=row, column=col, padx=2, pady=2)
                self.day_buttons.append(btn)

        ok_button = ttk.Button(self, text=T("OK"), command=self._confirm)
        ok_button.grid(row=8, column=0, columnspan=7, sticky="ew", padx=8, pady=(8, 10))

        self._render_calendar()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _cancel(self):
        self.result = ""
        self.destroy()

    def _confirm(self):
        if not self.result:
            self.result = datetime(self.current_year, self.current_month, 1).strftime("%d-%m-%Y")
        self.destroy()

    def _select_day(self, row, col):
        button = self.day_buttons[(row - 2) * 7 + col]
        text = button.cget("text")
        if not text:
            return
        self.result = datetime(self.current_year, self.current_month, int(text)).strftime("%d-%m-%Y")
        self.destroy()

    def prev_month(self):
        if self.current_month == 1:
            self.current_year -= 1
            self.current_month = 12
        else:
            self.current_month -= 1
        self._render_calendar()

    def next_month(self):
        if self.current_month == 12:
            self.current_year += 1
            self.current_month = 1
        else:
            self.current_month += 1
        self._render_calendar()

    def _render_calendar(self):
        month_title = datetime(self.current_year, self.current_month, 1).strftime("%B %Y")
        self.month_label.configure(text=month_title)

        first_weekday, days_in_month = calendar.monthrange(self.current_year, self.current_month)
        start_day = 1
        button_index = 0
        for _ in range(len(self.day_buttons)):
            self.day_buttons[button_index].configure(text="")
            button_index += 1

        button_index = 0
        for offset in range(first_weekday):
            self.day_buttons[button_index].configure(text="")
            button_index += 1

        for day in range(1, days_in_month + 1):
            self.day_buttons[button_index].configure(text=str(day))
            button_index += 1

        while button_index < len(self.day_buttons):
            self.day_buttons[button_index].configure(text="")
            button_index += 1


def pick_date(parent, initial_value=""):
    popup = DatePickerPopup(parent, initial_value=initial_value)
    parent.wait_window(popup)
    return popup.result


# Translation dictionary for English and Arabic labels used across the Tkinter interface.
TRANSLATIONS = {
    "eng": {
        "Tkinter could not start in this environment.": "Tkinter could not start in this environment.",
        "Please run this script in a normal Windows terminal or VS Code terminal, not in a headless/debug console.": "Please run this script in a normal Windows terminal or VS Code terminal, not in a headless/debug console.",
        "Client": "Client",
        "Client: {client_name}": "Client: {client_name}",
        "All Tasks": "All Tasks",
        "Pending Tasks": "Pending Tasks",
        "Mark Done": "Mark Done",
        "Close": "Close",
        "No task plan": "No task plan",
        "There is no active task plan to update.": "There is no active task plan to update.",
        "No task selected": "No task selected",
        "Select a task from the pending list first.": "Select a task from the pending list first.",
        "Client Progress Manager": "Clients Manager",
        "Welcome to Starco Commercial Complex": "Welcome to Starco Commercial Complex",
        "Welcome to Starco Commercial Complex Arabic": "مرحبًا بكم في مجمع ستاركو التجاري",
        "Overview": "Overview",
        "Exit": "Exit",
        "Client Details": "Client Details",
        "Client Name": "Client Name",
        "Country": "Country",
        "Contact": "Contact Number",
        "Business": "Business",
        "Shop Number": "Shop Number",
        "Address": "Address",
        "Electrical Meter": "Electrical Meter",
        "Email": "Email",
        "Client Review": "Client Review",
        "Add Review": "Add Review",
        "Open Review Log": "Open Review Log",
        "Add Client": "Add Client",
        "Create Client Plan": "Create Client Plan",
        "Save Client": "Save Client",
        "Delete Selected Client": "Delete Selected Client",
        "Progress Overview": "Progress Overview",
        "Progress": "Progress",
        "Total Tasks": "Total Tasks",
        "Tasks": "Tasks",
        "New task": "New task",
        "No client selected": "No client selected",
        "No pending tasks": "No pending tasks",
        "No tasks yet": "No tasks yet",
        "No client plan": "No client plan",
        "Create a client plan first.": "Create a client plan first.",
        "Missing client": "Missing client",
        "Please enter a client name.": "Please enter a client name.",
        "Missing contact": "Missing contact",
        "Please enter the client contact number.": "Please enter the client contact number.",
        "Missing business": "Missing business",
        "Please enter the client business type.": "Please enter the client business type.",
        "Missing tasks": "Missing tasks",
        "Enter at least one task or set a total task count greater than zero.": "Enter at least one task or set a total task count greater than zero.",
        "Review saved": "Review saved",
        "Review saved for '{name}'.": "Review saved for '{name}'.",
        "No review": "No review",
        "Please type a review before saving it.": "Please type a review before saving it.",
        "Client Reviews Log": "Client Reviews Log",
        "Date": "Date",
        "Review": "Review",
        "No reviews yet": "No reviews yet",
        "All Clients Progress": "All Clients Progress",
        "Edit Selected Client": "Edit Selected Client",
        "Refresh": "Refresh",
        "Home": "Home",
        "Delete client?": "Delete client?",
        "Are you sure you want to delete '{client_name}' from the client list?": "Are you sure you want to delete '{client_name}' from the client list?",
        "Client deleted": "Client deleted",
        "'{client_name}' was removed successfully.": "'{client_name}' was removed successfully.",
        "Client not found": "Client not found",
        "'{client_name}' was not found in the saved client list.": "'{client_name}' was not found in the saved client list.",
        "Saved progress only": "Saved progress only",
        "Select a client row first.": "Select a client row first.",
        "Select a client from the list first.": "Select a client from the list first.",
        "Add Task": "Add Task",
        "Tasks Details": "Tasks Details",
        "Contract Details": "Contract Details",
        "Preview": "Preview",
        "Close Preview": "Close Preview",
        "Save": "Save",
        "Edit": "Edit",
        "OK": "OK",
        "Refresh Progress": "Refresh Progress",
        "Payment Report": "Payment Report",
        "Save Comment": "Save Comment",
        "Share Client Info": "Share Client Info",
        "Contract Number": "Contract Number",
        "Starting Date": "Starting Date",
        "Ending Date": "Ending Date",
        "Commercial Registration Number": "Commercial Registration Number",
        "Authorized Signature Name": "Authorized Signature Name",
        "Rent Value": "Rent Value",
        "Currency Type": "Currency Type",
        "Open Issues Requiring Attention": "Open Issues Requiring Attention",
        "All Clients": "All Clients",
        "Open All Clients": "All Clients",
        "Project Manager To-Do": "Project Manager To-Do",
        "Open client payment records": "Open client payment records",
        "Follow up payment for {client_name} - {month}": "Follow up payment for {client_name} - {month}",
        "No pending payment follow-ups": "No pending payment follow-ups",
        "Transactions": "Transactions",
        "Client Transactions": "Client Transactions",
        "Month": "Month",
        "Status": "Status",
        "Amount": "Amount",
        "Payment Method": "Payment Method",
        "Cheque Number": "Cheque Number",
        "Due Date": "Due Date",
        "Bank Name": "Bank Name",
        "Reservation Status": "Reservation Status",
        "Shop Number to Reserve": "Shop Number to Reserve",
        "Deposit Money Received": "Deposit Money Received",
        "Preliminary Contract Status": "Preliminary Contract Status",
        "Deposit received": "Deposit received",
        "Deposit not received": "Deposit not received",
        "Completed": "Completed",
        "Under progress": "Under progress",
        "Add Month": "Add Month",
        "Save Transactions": "Save Transactions",
        "Transactions saved": "Transactions saved",
        "Client payment transactions were updated successfully.": "Client payment transactions were updated successfully.",
        "No payments yet": "No payments yet",
        "Send Email": "Send Email",
        "Save & Exit": "Save & Exit",
        "Cancel": "Cancel",
        "Proceed to exit": "Proceed to exit",
        "Please enter a client name before saving.": "Please enter a client name before saving.",
        "Please enter the client contact number before saving.": "Please enter the client contact number before saving.",
        "Please enter the client business type before saving.": "Please enter the client business type before saving.",
        "This client does not have an email saved yet.": "This client does not have an email saved yet.",
        "Select or create a client before adding a review.": "Select or create a client before adding a review.",
        "No email": "No email",
        "Exit app": "Exit app",
        "You are exiting the app. Ensure all entered data is saved; otherwise proceed to exit.": "You are exiting the app. Ensure all entered data is saved; otherwise proceed to exit.",
        "Task Details - {client_name}": "Task Details - {client_name}",
        "<New Client>": "<New Client>",
        "Select an existing client first.": "Select client first.",
        "Client saved": "Client saved",
        "'{name}' was saved successfully.": "'{name}' was saved successfully.",
        "No client plan": "No client plan",
        "Select a task from the pending list.": "Select a task from the pending list.",
        "Save Review": "Save Review",
        "Save Task": "Save Task",
        "Delete Tasks": "Delete Tasks",
        "Clients name missing": "Clients name missing",
        "Please fill the client name field first.": "Please fill the client name field first.",
        "No review": "No review",
        "Please type a review before saving it.": "Please type a review before saving it.",
        "Task {i}": "Task {i}",
        "Language": "Language",
        "English": "English",
        "العربية": "العربية",
        "Print": "Print",
        "Save Log": "Save Log",
        "Select file path": "Select file path",
        "Browse": "Browse",
        "Export Client Log": "Export Client Log",
        "Export Task Log": "Export Task Log",
        "Export Review Log": "Export Review Log",
        "Export Observation Log": "Export Review Log",
        "Export Clients Log": "Export Clients Log",
        "No printers registered on this laptop.": "No printers registered on this laptop.",
        "Copy vCard (.vcf)": "Copy vCard (.vcf)",
        "vCard (.vcf)": "vCard (.vcf)",
        "Client details copied to the clipboard.": "Client details copied to the clipboard.",
    },
    "ar": {
        "Tkinter could not start in this environment.": "تعذر启动 واجهة Tkinter في هذا البيئة.",
        "Please run this script in a normal Windows terminal or VS Code terminal, not in a headless/debug console.": "يرجى تشغيل هذا الملف من محطة Windows عادية أو من محطة VS Code، وليس من وحدة تحكم رأسية أو وضع التصحيح.",
        "Client": "العميل",
        "Client: {client_name}": "العميل: {client_name}",
        "All Tasks": "جميع المهام",
        "Pending Tasks": "المهام المعلقة",
        "Mark Done": "تم الإنجاز",
        "Close": "إغلاق",
        "No task plan": "لا توجد خطة مهام",
        "There is no active task plan to update.": "لا توجد خطة مهام نشطة لتحديثها.",
        "No task selected": "لم يتم تحديد أي مهمة",
        "Select a task from the pending list first.": "حدد مهمة من القائمة المعلقة أولاً.",
        "Client Progress Manager": "مدير العملاء",
        "Welcome to Starco Commercial Complex": "Welcome to Starco Commercial Complex",
        "Welcome to Starco Commercial Complex Arabic": "مرحبًا بكم في مجمع ستاركو التجاري",
        "Overview": "نظرة عامة",
        "Exit": "خروج",
        "Client Details": "تفاصيل العميل",
        "Client Name": "اسم العميل",
        "Country": "الدولة",
        "Contact": "رقم التواصل",
        "Business": "نوع النشاط",
        "Shop Number": "رقم المحل",
        "Address": "العنوان",
        "Electrical Meter": "عداد الكهرباء",
        "Email": "البريد الإلكتروني",
        "Client Review": "ملاحظات العميل",
        "Add Review": "إضافة ملاحظة",
        "Open Review Log": "فتح سجل الملاحظات",
        "Add Client": "إضافة عميل",
        "Create Client Plan": "إنشاء خطة العميل",
        "Save Client": "حفظ العميل",
        "Delete Selected Client": "حذف العميل المحدد",
        "Progress Overview": "نظرة عامة على التقدم",
        "Progress": "التقدم",
        "Total Tasks": "إجمالي المهام",
        "Tasks": "المهام",
        "New task": "مهمة جديدة",
        "No client selected": "لم يتم تحديد عميل",
        "No pending tasks": "لا توجد مهام معلقة",
        "No tasks yet": "لا توجد مهام بعد",
        "No client plan": "لا توجد خطة عميل",
        "Create a client plan first.": "أنشئ خطة العميل أولاً.",
        "Missing client": "اسم العميل مفقود",
        "Please enter a client name.": "يرجى إدخال اسم العميل.",
        "Missing contact": "رقم التواصل مفقود",
        "Please enter the client contact number.": "يرجى إدخال رقم التواصل الخاص بالعميل.",
        "Missing business": "نوع النشاط مفقود",
        "Please enter the client business type.": "يرجى إدخال نوع نشاط العميل.",
        "Missing tasks": "المهام مفقودة",
        "Enter at least one task or set a total task count greater than zero.": "أدخل مهمة واحدة على الأقل أو قم بتعيين إجمالي مهام أكبر من صفر.",
        "Review saved": "تم حفظ الملاحظة",
        "Review saved for '{name}'.": "تم حفظ الملاحظة للعميل '{name}'.",
        "No review": "لا توجد ملاحظة",
        "Please type a review before saving it.": "يرجى كتابة ملاحظة قبل حفظها.",
        "Client Reviews Log": "سجل ملاحظات العملاء",
        "Date": "التاريخ",
        "Review": "الملاحظة",
        "No reviews yet": "لا توجد ملاحظات بعد",
        "All Clients Progress": "تقدم جميع العملاء",
        "Edit Selected Client": "تعديل العميل المحدد",
        "Refresh": "تحديث",
        "Home": "الرئيسية",
        "Delete client?": "حذف العميل؟",
        "Are you sure you want to delete '{client_name}' from the client list?": "هل أنت متأكد أنك تريد حذف '{client_name}' من قائمة العملاء؟",
        "Client deleted": "تم حذف العميل",
        "'{client_name}' was removed successfully.": "تم حذف '{client_name}' بنجاح.",
        "Client not found": "لم يتم العثور على العميل",
        "'{client_name}' was not found in the saved client list.": "لم يتم العثور على '{client_name}' في قائمة العملاء المحفوظة.",
        "Saved progress only": "تقدم محفوظ فقط",
        "Select a client row first.": "حدد صف عميل أولاً.",
        "Select a client from the list first.": "حدد عميلًا من القائمة أولاً.",
        "Add Task": "إضافة مهمة",
        "Tasks Details": "تفاصيل المهام",
        "Contract Details": "تفاصيل العقد",
        "Preview": "معاينة",
        "Close Preview": "إغلاق المعاينة",
        "Save": "حفظ",
        "Edit": "تعديل",
        "OK": "موافق",
        "Refresh Progress": "تحديث التقدم",
        "Payment Report": "تقرير الدفع",
        "Save Comment": "حفظ التعليق",
        "Share Client Info": "مشاركة معلومات العميل",
        "Contract Number": "رقم العقد",
        "Starting Date": "تاريخ البداية",
        "Ending Date": "تاريخ النهاية",
        "Commercial Registration Number": "رقم السجل التجاري",
        "Authorized Signature Name": "اسم الممضي المفوض",
        "Rent Value": "قيمة الإيجار",
        "Currency Type": "نوع العملة",
        "Open Issues Requiring Attention": "المشكلات المفتوحة التي تحتاج إلى عناية",
        "All Clients": "جميع العملاء",
        "Open All Clients": "جميع العملاء",
        "Project Manager To-Do": "مدير المشاريع - المهام",
        "Open client payment records": "فتح سجلات الدفع للعميل",
        "Follow up payment for {client_name} - {month}": "متابعة الدفع لـ {client_name} - {month}",
        "No pending payment follow-ups": "لا توجد متابعة مستحقة للدفع",
        "Transactions": "المعاملات",
        "Client Transactions": "معاملات العميل",
        "Month": "الشهر",
        "Status": "الحالة",
        "Amount": "المبلغ",
        "Payment Method": "طريقة الدفع",
        "Cheque Number": "رقم الشيك",
        "Due Date": "تاريخ الاستحقاق",
        "Bank Name": "اسم البنك",
        "Reservation Status": "حالة الحجز",
        "Shop Number to Reserve": "رقم المحل المراد حجزه",
        "Deposit Money Received": "إيداع المال المستلم",
        "Preliminary Contract Status": "حالة العقد المبدئية",
        "Deposit received": "تم استلام الإيداع",
        "Deposit not received": "لم يتم استلام الإيداع",
        "Completed": "مكتمل",
        "Under progress": "قيد التنفيذ",
        "Add Month": "إضافة شهر",
        "Save Transactions": "حفظ المعاملات",
        "Transactions saved": "تم حفظ المعاملات",
        "Client payment transactions were updated successfully.": "تم تحديث معاملات دفع العميل بنجاح.",
        "No payments yet": "لا توجد مدفوعات بعد",
        "Send Email": "إرسال بريد إلكتروني",
        "Save & Exit": "حفظ والخروج",
        "Cancel": "إلغاء",
        "Proceed to exit": "متابعة الخروج",
        "Please enter a client name before saving.": "يرجى إدخال اسم العميل قبل الحفظ.",
        "Please enter the client contact number before saving.": "يرجى إدخال رقم التواصل الخاص بالعميل قبل الحفظ.",
        "Please enter the client business type before saving.": "يرجى إدخال نوع نشاط العميل قبل الحفظ.",
        "This client does not have an email saved yet.": "هذا العميل لا يحتوي على بريد إلكتروني محفوظ بعد.",
        "Select or create a client before adding a review.": "حدد عميلًا أو أنشئ عميلًا قبل إضافة ملاحظة.",
        "No email": "لا يوجد بريد إلكتروني",
        "Exit app": "الخروج من التطبيق",
        "You are exiting the app. Ensure all entered data is saved; otherwise proceed to exit.": "أنت تخرج من التطبيق. تأكد من حفظ جميع البيانات المدخلة، وإلا استمر في الخروج.",
        "Task Details - {client_name}": "تفاصيل المهام - {client_name}",
        "<New Client>": "<عميل جديد>",
        "Select an existing client first.": "حدد العميل أولاً.",
        "Client saved": "تم حفظ العميل",
        "'{name}' was saved successfully.": "تم حفظ '{name}' بنجاح.",
        "No client plan": "لا توجد خطة عميل",
        "Select a task from the pending list.": "حدد مهمة من القائمة المعلقة.",
        "Save Review": "حفظ الملاحظة",
        "Save Task": "حفظ المهمة",
        "Delete Tasks": "حذف المهام",
        "Clients name missing": "اسم العميل مفقود",
        "Please fill the client name field first.": "يرجى ملء حقل اسم العميل أولاً.",
        "No review": "لا توجد مراجعة",
        "Please type a review before saving it.": "يرجى كتابة ملاحظة قبل حفظها.",
        "Task {i}": "المهمة {i}",
        "Language": "اللغة",
        "English": "English",
        "العربية": "العربية",
        "Print": "طباعة",
        "Save Log": "حفظ السجل",
        "Select file path": "اختر مسار الملف",
        "Browse": "تصفح",
        "Export Client Log": "تصدير سجل العميل",
        "Export Task Log": "تصدير سجل المهام",
        "Export Review Log": "تصدير سجل المراجعات",
        "Export Observation Log": "تصدير سجل المراجعات",
        "Export Clients Log": "تصدير سجل العملاء",
        "No printers registered on this laptop.": "لا توجد طابعات مسجلة في هذا الجهاز.",
        "Copy vCard (.vcf)": "نسخ vCard (.vcf)",
        "vCard (.vcf)": "vCard (.vcf)",
        "Client details copied to the clipboard.": "تم نسخ تفاصيل العميل إلى الحافظة.",
    },
}


# Detect physically available printers so reports can be sent to a local Windows printer.
def get_registered_printers():
    if win32print is None:
        return []

    try:
        printers = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS,
            None,
            1,
        )
        return [printer[2] for printer in printers if isinstance(printer, tuple) and len(printer) >= 3]
    except Exception:
        return []


def print_report_document(title, lines):
    report_lines = append_report_footer(lines)
    safe_title = "".join(ch if ch.isalnum() or ch in " _-" else "_" for ch in str(title)).strip() or "report"
    printers = get_registered_printers()

    if not printers:
        messagebox.showwarning(T("Print"), T("No printers registered on this laptop."))
        return False

    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False, prefix=f"{safe_title}_") as temp_file:
            temp_file.write(str(title) + "\n")
            temp_file.write("=" * max(20, len(str(title))) + "\n\n")
            for line in report_lines:
                temp_file.write(str(line) + "\n")
            temp_path = temp_file.name

        if hasattr(os, "startfile"):
            try:
                default_printer = win32print.GetDefaultPrinter() if win32print is not None else None
            except Exception:
                default_printer = None

            if default_printer:
                try:
                    import win32api
                    win32api.ShellExecute(0, "printto", temp_path, f'"{default_printer}"', None, 0)
                    return True
                except Exception:
                    pass

            os.startfile(temp_path, "print")
            return True

        messagebox.showinfo(T("Print"), f"Printed report saved to: {temp_path}")
        return True
    except Exception as exc:
        messagebox.showerror(T("Print"), f"Unable to print report: {exc}")
        return False


def set_language(lang):
    global CURRENT_LANGUAGE
    code = str(lang or "eng").strip().lower()
    if code in ("ar", "arabic"):
        CURRENT_LANGUAGE = "ar"
    else:
        CURRENT_LANGUAGE = "eng"
    return CURRENT_LANGUAGE


# def T(text, **kwargs):
#     language_map = TRANSLATIONS.get(CURRENT_LANGUAGE, TRANSLATIONS["eng"])
#     translated = language_map.get(text, text)
#     if kwargs:
#         return translated.format(**kwargs)
#     return translated


def T(text, **kwargs):
    language_map = TRANSLATIONS.get(CURRENT_LANGUAGE, TRANSLATIONS["eng"])
    translated = language_map.get(text, text)

    if kwargs:
        translated = translated.format(**kwargs)

    if CURRENT_LANGUAGE == "ar":
        translated = apply_bidi_text(translated)

    return translated


def validate_translation_coverage():
    english_keys = set(TRANSLATIONS.get("eng", {}).keys())
    arabic_keys = set(TRANSLATIONS.get("ar", {}).keys())
    missing = sorted(key for key in english_keys if key not in arabic_keys)
    if missing:
        raise ValueError(
            "Missing Arabic translations for UI labels:\n" + "\n".join(f" - {key}" for key in missing[:50])
        )
    return None


def build_task_log_report_text(plan=None, client_name=""):
    lines = [T("Task log"), "====================", ""]

    if plan is not None:
        plan_client = getattr(plan, "client_name", "") or client_name
        if getattr(plan, "client", None) is not None and not plan_client:
            plan_client = getattr(plan.client, "name", "")
        name = str(plan_client or T("No client selected")).strip()
        progress = getattr(plan, "progress", 0)
        lines.extend([f"Client: {name}", f"Progress: {progress}%", ""])

        tasks = list(getattr(plan, "all_tasks", []) or [])
        if tasks:
            lines.extend(f"- {task}" for task in tasks)
        else:
            lines.append(T("No tasks yet"))
    else:
        lines.append(T("No task plan available"))

    return "\n".join(str(item) for item in lines).rstrip() + "\n"


def build_review_log_report_text(client_name="", review_text=""):
    lines = [T("Review log"), "====================", ""]
    name = str(client_name or T("No client selected")).strip()
    review = str(review_text or T("No review")).strip()
    lines.extend([f"Client: {name}", f"Review: {review}"])
    return "\n".join(str(item) for item in lines).rstrip() + "\n"


# Splash screen shown while the desktop app initializes and loads resources.
def build_startup_splash():
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.configure(bg="#09111d")
    splash.attributes("-topmost", True)
    splash.attributes("-alpha", 0.97)

    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    splash.geometry(f"{screen_width}x{screen_height}+0+0")

    backdrop = tk.Canvas(splash, width=screen_width, height=screen_height, highlightthickness=0, bg="#09111d")
    backdrop.pack(fill="both", expand=True)

    backdrop.create_rectangle(0, 0, screen_width, screen_height, fill="#09111d", outline="")
    backdrop.create_rectangle(160, 120, screen_width - 160, screen_height - 120, outline="#5eead4", width=2, fill="#0f172a")
    backdrop.create_rectangle(220, 180, screen_width - 220, screen_height - 180, outline="#93c5fd", width=1, fill="#111827")

    content = tk.Frame(splash, bg="#111827")
    content.place(relx=0.5, rely=0.5, anchor="center")
    content.configure(highlightthickness=1, highlightbackground="#93c5fd")

    glass_panel = tk.Label(
        content,
        bg="#1d2736",
        padx=44,
        pady=28,
        text="",
        relief="flat",
        bd=0,
    )
    glass_panel.pack(fill="both", expand=True)

    logo_label = tk.Label(
        glass_panel,
        bg="#1d2736",
        fg="#f5c451",
        font=("Segoe UI", 12, "bold"),
        text="★",
    )
    logo_label.pack()

    app_name_label = tk.Label(
        glass_panel,
        bg="#1d2736",
        fg="#f8fafc",
        font=("Segoe UI", 18, "bold"),
        text="",
        justify="center",
    )
    app_name_label.pack_forget()

    def show_logo():
        if APP_ICON is not None and APP_ICON.exists():
            try:
                if Image is not None and ImageTk is not None:
                    image = Image.open(APP_ICON)
                    image = image.resize((220, 220), getattr(Image, "Resampling", Image).LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    logo_label.configure(image=photo, compound="center", text="")
                    logo_label.image = photo
                else:
                    logo_label.configure(text="★")
            except Exception:
                logo_label.configure(text="★")

        def animate_logo(step=0):
            if step <= 18:
                next_size = 22 + step * 5
                logo_label.configure(font=("Segoe UI", int(next_size), "bold"))
                splash.after(35, lambda: animate_logo(step + 1))
                return

            splash.after(1000, lambda: show_app_name_sequence())

        def show_app_name_sequence(step=0):
            app_name_label.pack(pady=(18, 0))
            splash.attributes("-alpha", 1.0)

            app_name_texts = [
                "Clients Manager",
                "Clients Manager",
                "Clients Manager",
            ]

            if step < len(app_name_texts):
                app_name_label.configure(text=app_name_texts[step], font=("Segoe UI", 20, "bold"))
                splash.after(900, lambda: show_app_name_sequence(step + 1))
                return

            splash.after(800, lambda: splash.destroy())

        animate_logo()

    splash.after(600, lambda: show_logo())
    return splash


# Keep a single global app instance so the overview window can be reused instead of reopening repeatedly.
_ACTIVE_PROGRESS_APP = None
_ACTIVE_WELCOME_WINDOW = None


def close_welcome_window():
    global _ACTIVE_WELCOME_WINDOW
    if _ACTIVE_WELCOME_WINDOW is not None:
        try:
            if _ACTIVE_WELCOME_WINDOW.winfo_exists():
                _ACTIVE_WELCOME_WINDOW.destroy()
        except Exception:
            pass
        _ACTIVE_WELCOME_WINDOW = None


def open_overview_window(force_new=False):
    global _ACTIVE_PROGRESS_APP, _ACTIVE_WELCOME_WINDOW

    if force_new and _ACTIVE_PROGRESS_APP is not None:
        try:
            if _ACTIVE_PROGRESS_APP.winfo_exists():
                _ACTIVE_PROGRESS_APP.destroy()
        except Exception:
            pass
        _ACTIVE_PROGRESS_APP = None

    if _ACTIVE_PROGRESS_APP is not None:
        try:
            if _ACTIVE_PROGRESS_APP.winfo_exists():
                app = _ACTIVE_PROGRESS_APP
                try:
                    app.deiconify()
                    app.lift()
                    app.focus_set()
                    if hasattr(app, "focus_section"):
                        app.focus_section("overview")
                except Exception:
                    pass
                return app
        except Exception:
            pass

    if _ACTIVE_WELCOME_WINDOW is not None:
        try:
            if _ACTIVE_WELCOME_WINDOW.winfo_exists():
                _ACTIVE_WELCOME_WINDOW.destroy()
        except Exception:
            pass
        _ACTIVE_WELCOME_WINDOW = None

    app = ProgressApp()
    _ACTIVE_PROGRESS_APP = app
    return app


def open_welcome_home(force_new=False):
    global _ACTIVE_PROGRESS_APP, _ACTIVE_WELCOME_WINDOW

    if force_new and _ACTIVE_WELCOME_WINDOW is not None:
        try:
            if _ACTIVE_WELCOME_WINDOW.winfo_exists():
                _ACTIVE_WELCOME_WINDOW.destroy()
        except Exception:
            pass
        _ACTIVE_WELCOME_WINDOW = None

    if _ACTIVE_WELCOME_WINDOW is not None:
        try:
            if _ACTIVE_WELCOME_WINDOW.winfo_exists():
                welcome = _ACTIVE_WELCOME_WINDOW
                try:
                    welcome.deiconify()
                    welcome.lift()
                    welcome.focus_set()
                except Exception:
                    pass
                try:
                    if hasattr(welcome, "_refresh_login_status"):
                        welcome._refresh_login_status()
                except Exception:
                    pass
                return welcome
        except Exception:
            pass

    if _ACTIVE_PROGRESS_APP is not None:
        try:
            if _ACTIVE_PROGRESS_APP.winfo_exists():
                _ACTIVE_PROGRESS_APP.destroy()
        except Exception:
            pass
        _ACTIVE_PROGRESS_APP = None

    welcome = WelcomeWindow()
    _ACTIVE_WELCOME_WINDOW = welcome
    welcome.protocol("WM_DELETE_WINDOW", close_welcome_window)
    return welcome


def close_popup_and_return(window):
    if window is None:
        return

    parent = getattr(window, "previous_window", None)
    if parent is None and getattr(window, "master", None) is not None:
        parent = window.master

    try:
        window.destroy()
    except Exception:
        pass

    if parent is not None:
        try:
            if hasattr(parent, "winfo_exists") and parent.winfo_exists():
                parent.deiconify()
                parent.lift()
                parent.focus_set()
        except Exception:
            pass


# Landing screen with navigation to the main client overview and payment-transaction sections.
class WelcomeWindow(tk.Tk):
    def __init__(self):
        global _ACTIVE_WELCOME_WINDOW
        super().__init__()
        ensure_default_guest_session()
        _ACTIVE_WELCOME_WINDOW = self
        self.title(T("Starco Commercial Complex"))
        self.geometry("900x620")
        self.minsize(760, 520)
        self.configure(bg="#eef2ff")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.option_add("*Font", "{Segoe UI} 9")
        self.style.configure(".", font=("{Segoe UI}", 9))
        self.style.configure(
            "Action.TButton",
            padding=(12, 8),
            font=("{Segoe UI}", 9, "bold"),
            foreground="#111827",
            background="#dbeafe",
            borderwidth=1,
            relief="raised",
        )
        self.style.map(
            "Action.TButton",
            background=[("active", "#bfdbfe"), ("pressed", "#93c5fd")],
            foreground=[("active", "#111827"), ("pressed", "#111827")],
            relief=[("pressed", "sunken"), ("active", "raised")],
        )

        current_profile = CURRENT_SESSION_PROFILE.copy()
        self.user_name_var = tk.StringVar(value=current_profile.get("name", "Guest"))
        self.user_email_var = tk.StringVar(value=current_profile.get("email", "Guest"))
        self.login_status_var = tk.StringVar(value="")
        self.guest_mode = True

        shell = ttk.Frame(self, padding=(20, 18, 20, 14))
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=3)
        shell.columnconfigure(1, weight=2)
        shell.rowconfigure(2, weight=1)

        header = ttk.Frame(shell, padding=(18, 10, 18, 8))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")

        logo_label = tk.Label(header, bg="#eef2ff", fg="#f5c451", font=("{Segoe UI}", 18, "bold"))
        logo_label.pack(anchor="center")
        if APP_ICON is not None and APP_ICON.exists():
            try:
                if Image is not None and ImageTk is not None:
                    image = Image.open(APP_ICON)
                    image = image.resize((88, 88), getattr(Image, "Resampling", Image).LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    logo_label.configure(image=photo, compound="center", text="")
                    logo_label.image = photo
                else:
                    logo_label.configure(text="★")
            except Exception:
                logo_label.configure(text="★")
        else:
            logo_label.configure(text="★")

        title = ttk.Label(
            header,
            text=T("Welcome to Starco Commercial Complex"),
            font=("{Segoe UI}", 18, "bold"),
            foreground="#111827",
        )
        title.pack(anchor="center", pady=(8, 0))

        self.login_status_label = tk.Label(
            header,
            textvariable=self.login_status_var,
            font=("{Segoe UI}", 10, "bold"),
            fg="#ecfeff",
            bg="#0f766e",
            padx=12,
            pady=6,
            relief="flat",
            bd=0,
            justify="center",
        )
        self.login_status_label.pack(anchor="center", pady=(0, 4))

        subtitle = ttk.Label(
            header,
            text=T("Welcome to Starco Commercial Complex Arabic"),
            font=("{Segoe UI}", 12),
            foreground="#374151",
        )
        subtitle.pack(anchor="center", pady=(0, 2))

        self._refresh_login_status()

        actions = ttk.Frame(shell, padding=(0, 0, 0, 8))
        actions.grid(row=1, column=0, columnspan=2, sticky="ew")
        actions.columnconfigure(0, weight=1)
        access_buttons = ttk.Frame(actions)
        access_buttons.pack(fill="x")

        guest_button = ttk.Button(access_buttons, text=T("Guest"), command=self.use_guest_profile, style="Action.TButton")
        guest_button.pack(side="left", padx=(0, 8))
        register_button = ttk.Button(access_buttons, text=T("Register"), command=self.open_registration_window, style="Action.TButton")
        register_button.pack(side="left", padx=(0, 8))
        login_button = ttk.Button(access_buttons, text=T("Login"), command=self.open_login_window, style="Action.TButton")
        login_button.pack(side="left", padx=(0, 8))
        logout_button = ttk.Button(access_buttons, text=T("Logout"), command=self.logout_user, style="Action.TButton")
        logout_button.pack(side="left")

        content = ttk.Frame(shell)
        content.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(4, 8))
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        todo_card = ttk.LabelFrame(content, text=T("Project Manager To-Do"), padding=(12, 10))
        todo_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        todo_card.columnconfigure(0, weight=1)
        todo_card.rowconfigure(0, weight=1)

        self.todo_listbox = tk.Listbox(
            todo_card,
            height=10,
            width=46,
            exportselection=False,
            bg="#fffdf3",
            relief="solid",
            borderwidth=1,
            font=("{Segoe UI}", 10),
        )
        self.todo_listbox.grid(row=0, column=0, sticky="nsew")
        todo_card.rowconfigure(0, weight=1)
        self.refresh_todo_list()

        action_card = ttk.LabelFrame(content, text=T("Quick Actions"), padding=(12, 10))
        action_card.grid(row=0, column=1, sticky="nsew")
        action_card.columnconfigure(0, weight=1)
        action_card.columnconfigure(1, weight=1)

        self.overview_button = ttk.Button(
            action_card,
            text=T("Overview"),
            command=self._open_progress_panel,
            style="Action.TButton",
            width=16,
        )
        self.overview_button.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))

        self.transactions_button = ttk.Button(
            action_card,
            text=T("Transactions"),
            command=self._open_transactions_panel,
            style="Action.TButton",
            width=16,
        )
        self.transactions_button.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))

        self.rent_calculator_button = ttk.Button(
            action_card,
            text=T("Rent Calculator"),
            command=self.open_rent_calculator_window,
            style="Action.TButton",
            width=16,
        )
        self.rent_calculator_button.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))

        self.contract_button = ttk.Button(
            action_card,
            text=T("Reservation Contract"),
            command=self.open_reservation_contract_form,
            style="Action.TButton",
            width=16,
        )
        self.contract_button.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))

        self.payment_report_button = ttk.Button(
            action_card,
            text=T("Payment Report"),
            command=self.open_payment_report_window,
            style="Action.TButton",
            width=18,
        )
        self.payment_report_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        contract_frame = ttk.LabelFrame(shell, text=T("Saved Reservation Contracts"), padding=(12, 10))
        contract_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")
        contract_frame.columnconfigure(0, weight=1)

        search_row = ttk.Frame(contract_frame)
        search_row.pack(fill="x", pady=(0, 8))
        ttk.Label(search_row, text=T("Search")).pack(side="left", padx=(0, 8))
        self.saved_contract_search_var = tk.StringVar()
        self.saved_contract_search_var.trace_add("write", self._refresh_saved_contract_list)
        ttk.Entry(search_row, textvariable=self.saved_contract_search_var).pack(side="left", fill="x", expand=True)

        self.saved_contract_listbox = tk.Listbox(
            contract_frame,
            height=6,
            exportselection=False,
            bg="#f8fafc",
            relief="solid",
            borderwidth=1,
            font=("{Segoe UI}", 9),
        )
        self.saved_contract_listbox.pack(fill="both", expand=True)
        self.saved_contract_lookup = {}

        action_row = ttk.Frame(contract_frame)
        action_row.pack(fill="x", pady=(8, 0))
        ttk.Button(action_row, text=T("Preview"), command=self.preview_selected_saved_contract, style="Action.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text=T("Print"), command=self.print_selected_saved_contract, style="Action.TButton").pack(side="left")

        self._refresh_saved_contract_list()

        footer = ttk.Frame(self, padding=(0, 0, 18, 12))
        footer.pack(fill="x")
        exit_button = ttk.Button(footer, text=T("Exit"), command=self.exit_app, style="Action.TButton", width=14)
        exit_button.pack(anchor="center")
        self.protocol("WM_DELETE_WINDOW", self.close_welcome_window)

    def close_welcome_window(self):
        global _ACTIVE_WELCOME_WINDOW
        if _ACTIVE_WELCOME_WINDOW is self:
            _ACTIVE_WELCOME_WINDOW = None
        self.destroy()
        try:
            self.quit()
        except Exception:
            pass

    def exit_app(self):
        sync_session_profile(clear=True)
        self.user_name_var.set("")
        self.user_email_var.set("")
        self.login_status_var.set("")
        self.guest_mode = True
        self.close_welcome_window()

    def _open_progress_panel(self):
        self.destroy()
        app = open_overview_window()
        app.focus_section("overview")

    def _open_transactions_panel(self):
        if not is_registered_user_profile():
            messagebox.showwarning(T("Access Denied"), T("Registered users only. Guest access is limited to clients, reviews and tasks."))
            return
        self.destroy()
        app = open_overview_window()
        try:
            app.deiconify()
            app.lift()
            app.focus_set()
        except Exception:
            pass
        try:
            app.focus_section("overview")
            app.open_transactions_window()
        except Exception:
            pass

    def _get_saved_contract_index_path(self):
        return APP_ROOT / "application_outputs" / "contracts" / "reservation_contracts.json"

    def _load_saved_contract_entries(self):
        index_path = self._get_saved_contract_index_path()
        if not index_path.exists():
            return []

        try:
            with index_path.open("r", encoding="utf-8") as infile:
                payload = json.load(infile)
        except (json.JSONDecodeError, OSError, TypeError):
            return []

        if not isinstance(payload, dict):
            return []

        entries = []
        for key, value in payload.items():
            if not isinstance(value, str):
                continue
            contract_path = Path(value)
            if contract_path.exists():
                entries.append((str(key), str(contract_path)))
        entries.sort(key=lambda item: item[0].lower())
        return entries

    def _refresh_saved_contract_list(self, *_args):
        query = self.saved_contract_search_var.get().strip().lower()
        entries = self._load_saved_contract_entries()
        filtered = []
        for key, path in entries:
            if not query or query in key.lower() or query in Path(path).stem.lower():
                filtered.append((key, path))

        self.saved_contract_lookup = {}
        self.saved_contract_listbox.delete(0, tk.END)
        if not filtered:
            self.saved_contract_listbox.insert(tk.END, "No saved contracts found")
            return

        for key, path in filtered:
            label = f"{key} - {Path(path).name}"
            self.saved_contract_lookup[label] = path
            self.saved_contract_listbox.insert(tk.END, label)

    def preview_selected_saved_contract(self):
        if not self.saved_contract_listbox.curselection():
            messagebox.showwarning(T("Preview"), T("Please select a saved contract first."))
            return

        selected_label = self.saved_contract_listbox.get(self.saved_contract_listbox.curselection()[0])
        contract_path = self.saved_contract_lookup.get(selected_label)
        if not contract_path or not Path(contract_path).exists():
            messagebox.showwarning(T("Preview"), T("The selected contract file could not be found."))
            return

        try:
            if hasattr(os, "startfile"):
                os.startfile(contract_path)
            elif os.name == "nt":
                subprocess.Popen(["notepad.exe", contract_path])
            else:
                subprocess.Popen(["xdg-open", contract_path])
        except Exception as exc:
            messagebox.showerror(T("Preview"), T("Unable to open contract: {exc}", exc=exc))

    def print_selected_saved_contract(self):
        if not self.saved_contract_listbox.curselection():
            messagebox.showwarning(T("Print"), T("Please select a saved contract first."))
            return

        selected_label = self.saved_contract_listbox.get(self.saved_contract_listbox.curselection()[0])
        contract_path = self.saved_contract_lookup.get(selected_label)
        if not contract_path or not Path(contract_path).exists():
            messagebox.showwarning(T("Print"), T("The selected contract file could not be found."))
            return

        try:
            if hasattr(os, "startfile"):
                os.startfile(contract_path, "print")
            elif os.name == "nt":
                subprocess.Popen(["notepad.exe", "/p", contract_path])
            else:
                subprocess.Popen(["xdg-open", contract_path])
        except Exception as exc:
            messagebox.showerror(T("Print"), T("Unable to print contract: {exc}", exc=exc))

    def open_rent_calculator_window(self):
        calculator = RentCalculatorWindow(self)
        calculator.grab_set()
        calculator.wait_window()

    def open_payment_report_window(self):
        if is_guest_profile(CURRENT_SESSION_PROFILE):
            messagebox.showwarning(T("Access Denied"), T("Guest users cannot open payment reports. Overview is read-only."))
            return
        report_window = ClientPaymentReportWindow(self)
        report_window.grab_set()
        report_window.wait_window()

    def open_login_window(self):
        login_window = LoginWindow(self)
        login_window.grab_set()
        login_window.wait_window()
        self._refresh_login_status()

    def open_registration_window(self):
        previous_profile = {
            "name": (self.user_name_var.get() or CURRENT_SESSION_PROFILE.get("name") or "").strip(),
            "email": (self.user_email_var.get() or CURRENT_SESSION_PROFILE.get("email") or "").strip(),
        }

        registration = UserRegistrationWindow(self)
        registration.grab_set()
        registration.wait_window()

        if previous_profile["name"] or previous_profile["email"]:
            self.user_name_var.set(previous_profile["name"])
            self.user_email_var.set(previous_profile["email"])
            set_current_session_profile(user_name=previous_profile["name"], user_email=previous_profile["email"])
        else:
            self.user_name_var.set("Guest")
            self.user_email_var.set("Guest")
            set_current_session_profile(user_name="Guest", user_email="Guest")

        self._refresh_login_status()

    def use_guest_profile(self):
        profile = save_guest_profile("Guest", "Guest")
        sync_session_profile(user_name=profile["name"], user_email=profile["email"])
        self.user_name_var.set(profile["name"])
        self.user_email_var.set(profile["email"])
        self._refresh_login_status()

    def _apply_logged_in_user(self, user_name, user_email):
        set_current_session_profile(user_name=user_name, user_email=user_email)
        self.user_name_var.set(user_name)
        self.user_email_var.set(user_email)
        self._refresh_login_status()

    def open_reservation_contract_form(self):
        if not is_registered_user_profile():
            messagebox.showwarning(T("Access Denied"), T("Registered users only can open the reservation contract form."))
            return

        try:
            from ui.reservation_contract import ShopReservationForm
        except ImportError:
            messagebox.showerror(T("Form unavailable"), T("The reservation contract form could not be loaded."))
            return

        form = ShopReservationForm()
        form.grab_set()
        form.wait_window()

    def _sync_overview_access(self):
        if not self.winfo_exists():
            return

        overview_widget = getattr(self, "overview_button", None)
        if overview_widget is not None:
            try:
                if overview_widget.winfo_exists():
                    overview_widget.configure(state="normal")
            except Exception:
                pass

        contract_widget = getattr(self, "contract_button", None)
        if contract_widget is not None:
            try:
                if contract_widget.winfo_exists():
                    contract_widget.configure(
                        state="normal" if is_registered_user_profile() else "disabled"
                    )
            except Exception:
                pass

    def _refresh_login_status(self):
        if not self.winfo_exists():
            return

        session_name = CURRENT_SESSION_PROFILE.get("name", "").strip()
        session_email = CURRENT_SESSION_PROFILE.get("email", "").strip()
        profile = {
            "name": (self.user_name_var.get().strip() or session_name),
            "email": (self.user_email_var.get().strip() or session_email),
        }
        if profile["name"] or profile["email"]:
            self.user_name_var.set(profile["name"])
            self.user_email_var.set(profile["email"])
            if is_registered_user_profile(profile):
                self.guest_mode = False
                self.login_status_var.set(T("Logged in as: {user_name}", user_name=profile["name"]))
                self._sync_overview_access()
                return

            self.guest_mode = True
            self.login_status_var.set(T("Logged in as: {user_name}", user_name=profile["name"] or "Guest"))
            self._sync_overview_access()
            return

        self.guest_mode = True
        self.login_status_var.set("")
        self._sync_overview_access()

    def login_user(self):
        user_name = self.user_name_var.get().strip()
        user_email = self.user_email_var.get().strip()

        if not user_name:
            messagebox.showwarning(T("User Name"), T("Please enter your user name."))
            return

        if not user_email:
            messagebox.showwarning(T("User Email"), T("Please enter your email address."))
            return

        if is_guest_login_credentials(user_name, user_email):
            save_guest_profile(user_name, user_email)
            self.guest_mode = True
            self.user_name_var.set(user_name)
            self.user_email_var.set(user_email)
            set_current_session_profile(user_name=user_name, user_email=user_email)
            self._refresh_login_status()
            messagebox.showinfo(T("Login"), T("Guest read-only access enabled. Overview is view-only."))
            return

        if not verify_registered_user(user_name, user_email):
            self.guest_mode = True
            self.user_name_var.set(user_name)
            self.user_email_var.set(user_email)
            set_current_session_profile(user_name=user_name, user_email=user_email)
            self._refresh_login_status()
            messagebox.showwarning(
                T("Login failed"),
                T("User not found in the saved user list. Please register first or continue as guest."),
            )
            return

        self.guest_mode = False
        save_user_profile(user_name, user_email)
        set_current_session_profile(user_name=user_name, user_email=user_email)
        self.user_name_var.set(user_name)
        self.user_email_var.set(user_email)
        self._refresh_login_status()
        messagebox.showinfo(T("Login"), T("Login successful. Access granted to the app."))

    def refresh_todo_list(self):
        if not hasattr(self, "todo_listbox") or self.todo_listbox is None:
            return
        try:
            if not self.todo_listbox.winfo_exists():
                return
        except Exception:
            return

        try:
            self.todo_listbox.delete(0, tk.END)
        except Exception:
            return

        for task in self.generate_project_manager_todo_tasks():
            try:
                self.todo_listbox.insert(tk.END, task)
            except Exception:
                break

    def generate_project_manager_todo_tasks(self):
        manager = ClientManager(resolve_clients_data_path())
        manager.load_clients()
        tasks = []
        for client in manager.clients:
            contract_details = getattr(client, "contract_details", {}) or {}
            start_date = str(contract_details.get("starting_date") or "").strip()
            end_date = str(contract_details.get("ending_date") or "").strip()
            months = generate_contract_months(start_date, end_date)
            if not months:
                continue

            transactions_by_month = {}
            for entry in getattr(client, "transactions", []) or []:
                month = str(entry.get("month", "") or "").strip()
                if month:
                    transactions_by_month[month] = entry

            for month in months:
                entry = transactions_by_month.get(month)
                status = str((entry or {}).get("status", "") or "").strip().lower()
                if entry is not None and status in {"paid", "completed", "complete", "success", "successful"}:
                    continue
                tasks.append(f"Follow up payment for {client.name} - {month}")

        if not tasks:
            tasks.append("No pending payment follow-ups")
        return tasks

    def logout_user(self):
        sync_session_profile(clear=True)
        self.user_name_var.set("")
        self.user_email_var.set("")
        self.guest_mode = True
        self.login_status_var.set("")
        self._refresh_login_status()
        messagebox.showinfo(T("Logout"), T("You have logged out and returned to guest access."))
        self.destroy()

        global _ACTIVE_PROGRESS_APP
        if _ACTIVE_PROGRESS_APP is not None:
            try:
                if _ACTIVE_PROGRESS_APP.winfo_exists():
                    _ACTIVE_PROGRESS_APP.destroy()
            except Exception:
                pass
            _ACTIVE_PROGRESS_APP = None

        welcome = WelcomeWindow()
        welcome.protocol("WM_DELETE_WINDOW", welcome.destroy)
        welcome.mainloop()

    def save_user_profile(self):
        user_name = self.user_name_var.get().strip()
        user_email = self.user_email_var.get().strip()
        if not user_name:
            messagebox.showwarning(T("User Name"), T("Please enter your user name."))
            return

        if not user_email:
            messagebox.showwarning(T("User Email"), T("Please enter your email address."))
            return

        if not is_admin_registration_allowed(user_name, user_email):
            messagebox.showwarning(T("User Registration"), T("Registration is only available for Admin/Admin."))
            return

        if is_guest_login_credentials(user_name, user_email):
            save_guest_profile(user_name, user_email)
            self.guest_mode = True
            self.user_name_var.set(user_name)
            self.user_email_var.set(user_email)
            set_current_session_profile(user_name=user_name, user_email=user_email)
            self._refresh_login_status()
            messagebox.showinfo(
                T("User Login"),
                T("Guest read-only access enabled. Overview is view-only."),
            )
            return

        if not verify_registered_user(user_name, user_email):
            self.guest_mode = True
            self.user_name_var.set(user_name)
            self.user_email_var.set(user_email)
            set_current_session_profile(user_name=user_name, user_email=user_email)
            self._refresh_login_status()
            messagebox.showinfo(
                T("User Login"),
                T("User not found. Access granted as guest. Transactions, contract details, and email sending stay restricted."),
            )
            return

        self.guest_mode = False
        save_user_profile(user_name, user_email)
        set_current_session_profile(user_name=user_name, user_email=user_email)
        self.user_name_var.set(user_name)
        self.user_email_var.set(user_email)
        self._refresh_login_status()
        messagebox.showinfo(T("User Profile"), T("User profile confirmed successfully."))


class RentCalculatorWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.previous_window = master
        self.title(T("Rent Calculator"))
        self.geometry("430x300")
        self.minsize(380, 260)
        self.configure(bg="#f8fafc")
        self.protocol("WM_DELETE_WINDOW", self.go_back)

        container = ttk.Frame(self, padding=18)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text=T("Rent Calculator"), font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))

        ttk.Label(container, text=T("Rent per remaining shop (OMR)"), anchor="w").pack(anchor="w", pady=(0, 4))
        self.per_shop_rent_var = tk.StringVar(value="0")
        ttk.Entry(container, textvariable=self.per_shop_rent_var, width=26).pack(fill="x", pady=(0, 12))

        ttk.Button(container, text=T("Calculate"), command=self.calculate).pack(anchor="w", pady=(0, 12))

        ttk.Label(container, text=T("Total rent from all saved clients"), anchor="w").pack(anchor="w")
        self.total_rent_var = tk.StringVar(value="0.00")
        ttk.Label(container, textvariable=self.total_rent_var, font=("Segoe UI", 11, "bold"), foreground="#0f172a").pack(anchor="w", pady=(0, 8))

        ttk.Label(container, text=T("Remaining shops available"), anchor="w").pack(anchor="w")
        self.remaining_shop_var = tk.StringVar(value="0")
        ttk.Label(container, textvariable=self.remaining_shop_var, font=("Segoe UI", 11, "bold"), foreground="#0f172a").pack(anchor="w", pady=(0, 4))

        ttk.Label(container, text=T("Total rent for remaining shops"), anchor="w").pack(anchor="w")
        self.remaining_rent_var = tk.StringVar(value="0.00")
        ttk.Label(container, textvariable=self.remaining_rent_var, font=("Segoe UI", 11, "bold"), foreground="#0f172a").pack(anchor="w")

        ttk.Button(container, text=T("Back"), command=self.go_back).pack(anchor="e", pady=(16, 0))
        self.calculate()

    def go_back(self):
        close_popup_and_return(self)

    def _load_clients(self):
        manager = ClientManager(resolve_clients_data_path())
        manager.load_clients()
        return manager.clients

    def _load_used_shop_numbers(self):
        used = set()
        for client in self._load_clients():
            shop_number = str(getattr(client, "shop_number", "") or "").strip()
            if shop_number:
                used.add(shop_number)
        return used

    def calculate(self):
        clients = self._load_clients()
        total_saved = calculate_total_saved_client_rent(clients)
        used_shops = self._load_used_shop_numbers()
        remaining = calculate_remaining_shop_count(used_shops)
        per_shop_rent = _coerce_currency_amount(self.per_shop_rent_var.get())
        remaining_rent = calculate_remaining_shop_rent(used_shops, per_shop_rent)

        self.total_rent_var.set(f"{total_saved:.2f} OMR")
        self.remaining_shop_var.set(f"{remaining} shops")
        self.remaining_rent_var.set(f"{remaining_rent:.2f} OMR")


class LoginWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.previous_window = master
        self.title(T("User Login"))
        self.geometry("420x220")
        self.minsize(340, 180)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.go_back)

        self.user_name_var = tk.StringVar(value=(master.user_name_var.get() if master is not None and hasattr(master, "user_name_var") else ""))
        self.user_email_var = tk.StringVar(value=(master.user_email_var.get() if master is not None and hasattr(master, "user_email_var") else ""))

        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text=T("User Name")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(main, textvariable=self.user_name_var, width=32).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(main, text=T("User Email")).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(main, textvariable=self.user_email_var, width=32).grid(row=1, column=1, sticky="ew", pady=(0, 8))

        actions = ttk.Frame(main)
        actions.grid(row=2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(actions, text=T("Login"), command=self.login_user).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text=T("Reset"), command=self.reset_fields).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text=T("Back"), command=self.go_back).pack(side="left")

    def go_back(self):
        close_popup_and_return(self)

    def reset_fields(self):
        self.user_name_var.set("")
        self.user_email_var.set("")

    def close_to_welcome(self):
        self.go_back()

    def login_user(self):
        user_name = self.user_name_var.get().strip()
        user_email = self.user_email_var.get().strip()

        if not user_name:
            messagebox.showwarning(T("User Name"), T("Please enter your user name."))
            return

        if not user_email:
            messagebox.showwarning(T("User Email"), T("Please enter your email address."))
            return

        if is_guest_login_credentials(user_name, user_email):
            save_guest_profile(user_name, user_email)
            if self.master is not None and hasattr(self.master, "_apply_logged_in_user"):
                self.master._apply_logged_in_user(user_name, user_email)
            self.destroy()
            messagebox.showinfo(T("Login"), T("Guest read-only access enabled. Overview is view-only."))
            return

        if not verify_registered_user(user_name, user_email):
            if self.master is not None and hasattr(self.master, "_apply_logged_in_user"):
                self.master._apply_logged_in_user(user_name, user_email)
            messagebox.showwarning(
                T("Login failed"),
                T("User not found in the saved user list. Please register first or continue as guest."),
            )
            return

        save_user_profile(user_name, user_email)
        if self.master is not None and hasattr(self.master, "_apply_logged_in_user"):
            self.master._apply_logged_in_user(user_name, user_email)
        self.destroy()
        messagebox.showinfo(T("Login"), T("Login successful. Access granted to the app."))


class UserRegistrationWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.previous_window = master
        self.title(T("User Registration"))
        self.geometry("420x220")
        self.minsize(340, 180)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.go_back)

        self.user_name_var = tk.StringVar(value="")
        self.user_email_var = tk.StringVar(value="")
        self.registration_status_var = tk.StringVar(value="Registration disabled")
        self.editing_enabled = False

        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text=T("User Name")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(main, textvariable=self.user_name_var, width=32).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(main, text=T("User Email")).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(main, textvariable=self.user_email_var, width=32).grid(row=1, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(main, textvariable=self.registration_status_var, foreground="#0f766e", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 8))

        actions = ttk.Frame(main)
        actions.grid(row=3, column=0, columnspan=2, sticky="e", pady=(8, 0))
        self.confirm_edit_button = ttk.Button(actions, text=T("Confirm"), command=self.confirm_admin_access, state="disabled")
        self.confirm_edit_button.pack(side="left", padx=(0, 8))
        self.save_user_button = ttk.Button(actions, text=T("Save User"), command=self.register_user, state="disabled")
        self.save_user_button.pack(side="left", padx=(0, 8))
        ttk.Button(actions, text=T("Reset"), command=self.reset_fields).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text=T("Back"), command=self.go_back).pack(side="left")

        self.user_name_var.trace_add("write", lambda *_: self.update_registration_state())
        self.user_email_var.trace_add("write", lambda *_: self.update_registration_state())
        self.update_registration_state()

    def confirm_admin_access(self):
        user_name = self.user_name_var.get().strip()
        user_email = self.user_email_var.get().strip()

        if not is_admin_registration_allowed(user_name, user_email):
            self.registration_status_var.set("Registration disabled")
            self.save_user_button.configure(state="disabled")
            return

        self.editing_enabled = True
        self.user_name_var.set("")
        self.user_email_var.set("")
        self.registration_status_var.set("Editing enabled")
        self.confirm_edit_button.configure(state="disabled")
        self.save_user_button.configure(state="disabled")

    def update_registration_state(self):
        user_name = self.user_name_var.get().strip()
        user_email = self.user_email_var.get().strip()
        admin_mode = user_name.lower() == "admin" and user_email.lower() == "admin"
        has_new_user_entry = bool(user_name) and bool(user_email) and not admin_mode

        if admin_mode:
            self.registration_status_var.set("Editing enabled")
            self.confirm_edit_button.configure(state="normal")
            self.save_user_button.configure(state="disabled")
            return

        if self.editing_enabled and has_new_user_entry:
            self.registration_status_var.set("Registration enabled")
            self.save_user_button.configure(state="normal")
            return

        if self.editing_enabled:
            self.registration_status_var.set("Editing enabled")
            self.save_user_button.configure(state="disabled")
            return

        self.registration_status_var.set("Registration disabled")
        self.confirm_edit_button.configure(state="disabled")
        self.save_user_button.configure(state="disabled")

    def reset_fields(self):
        self.editing_enabled = False
        self.user_name_var.set("")
        self.user_email_var.set("")
        self.registration_status_var.set("Registration disabled")
        self.confirm_edit_button.configure(state="disabled")
        self.save_user_button.configure(state="disabled")

    def go_back(self):
        close_popup_and_return(self)

    def close_to_login(self):
        self.go_back()

    def register_user(self):
        user_name = self.user_name_var.get().strip()
        user_email = self.user_email_var.get().strip()
        if not user_name:
            messagebox.showwarning(T("User Name"), T("Please enter your user name."))
            return

        if not user_email:
            messagebox.showwarning(T("User Email"), T("Please enter your email address."))
            return

        if not is_registration_submission_allowed(user_name, user_email):
            messagebox.showwarning(T("User Registration"), T("Please enter both a valid user name and email address."))
            return

        profile = user_registeration(user_name, user_email)
        if not profile.get("name") or not profile.get("email"):
            messagebox.showwarning(T("User Registration"), T("Please enter a valid user name and email address."))
            return

        set_current_session_profile(user_name=profile.get("name", ""), user_email=profile.get("email", ""))

        if self.master is not None and hasattr(self.master, "user_name_var"):
            self.master.user_name_var.set(profile.get("name", ""))
        if self.master is not None and hasattr(self.master, "user_email_var"):
            self.master.user_email_var.set(profile.get("email", ""))
        if self.master is not None and hasattr(self.master, "_refresh_login_status"):
            self.master._refresh_login_status()

        messagebox.showinfo(T("User Registration"), T("User registered successfully. Please log in with your saved credentials."))
        self.destroy()
        if self.master is not None and hasattr(self.master, "focus_set"):
            try:
                self.master.focus_set()
            except Exception:
                pass

    def generate_project_manager_todo_tasks(self):
        manager = ClientManager("clients.json")
        manager.load_clients()
        tasks = []
        for client in manager.clients:
            contract_details = getattr(client, "contract_details", {}) or {}
            start_date = str(contract_details.get("starting_date") or "").strip()
            end_date = str(contract_details.get("ending_date") or "").strip()
            months = generate_contract_months(start_date, end_date)
            if not months:
                continue

            transactions_by_month = {}
            for entry in getattr(client, "transactions", []) or []:
                month = str(entry.get("month", "") or "").strip()
                if month:
                    transactions_by_month[month] = entry

            for month in months:
                entry = transactions_by_month.get(month)
                status = str((entry or {}).get("status", "") or "").strip().lower()
                if entry is not None and status in {"paid", "completed", "complete", "success", "successful"}:
                    continue
                tasks.append(f"Follow up payment for {client.name} - {month}")

        if not tasks:
            tasks.append("No pending payment follow-ups")
        return tasks

    def refresh_todo_list(self):
        self.todo_listbox.delete(0, tk.END)
        for task in self.generate_project_manager_todo_tasks():
            self.todo_listbox.insert(tk.END, task)

    def _open_progress_panel(self):
        self.destroy()
        app = open_overview_window()
        app.focus_section("overview")

    def _open_transactions_panel(self):
        if not is_registered_user_profile():
            messagebox.showwarning(T("Access Denied"), T("Registered users only. Guest access is limited to clients, reviews and tasks."))
            return
        self.destroy()
        app = open_overview_window()
        try:
            app.deiconify()
            app.lift()
            app.focus_set()
        except Exception:
            pass
        try:
            app.focus_section("overview")
            app.open_transactions_window()
        except Exception:
            pass


def safe_main():
    try:
        splash = build_startup_splash()

        def launch_welcome_window():
            splash.destroy()
            welcome = WelcomeWindow()
            welcome.mainloop()

        splash.after(4000, launch_welcome_window)
        splash.mainloop()
    except tk.TclError as exc:
        message = (
            T("Tkinter could not start in this environment.") + "\n\n"
            + T("Please run this script in a normal Windows terminal or VS Code terminal, not in a headless/debug console.")
            + f"\n\nDetails: {exc}"
        )
        print(message, file=sys.stderr)
        raise SystemExit(1)


def parse_task_items(raw_value, fallback_total=0):
    text = (raw_value or "").strip()
    if not text:
        if fallback_total <= 0:
            return []
        return [str(i) for i in range(1, fallback_total + 1)]

    items = []
    for chunk in re.split(r"[\n,;]+", text):
        task = strip_task_number_prefix(chunk)
        if task:
            items.append(task)

    return items


# Task-plan model used to calculate progress and maintain the per-client task list.
class Plan:
    Clients_progress = {}

    def __init__(self, client: Client, all_tasks=None):
        self.client = client
        self.client_name = client.name
        self.all_tasks = list(all_tasks) if all_tasks else []
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
            "client_name": self.client.name,
            "progress": self.progress,
            "pending_tasks": list(self.pending_tasks),
            "all_tasks": list(self.all_tasks),
        }
        Plan.Clients_progress[self.client.name] = progress_data
        if hasattr(self.client, "progress"):
            self.client.progress = dict(progress_data)

    def to_dict(self):
        return {
            "client_name": self.client_name,
            "progress": self.progress,
            "pending_tasks": list(self.pending_tasks),
            "all_tasks": list(self.all_tasks),
        }


# Window for adding, editing, and completing tasks within a selected client's plan.
class TaskDetailsWindow(tk.Toplevel):
    def __init__(self, master=None, client_name="Client", plan=None, all_tasks=None, pending_tasks=None):
        super().__init__(master)
        self.title(T("Task Details - {client_name}", client_name=client_name))
        self.geometry("820x620")
        self.minsize(620, 420)

        self.plan = plan
        self.master_app = master

        main = ttk.Frame(self, padding=14)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text=T("Client: {client_name}", client_name=client_name), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))

        task_columns = ttk.Frame(main)
        task_columns.pack(fill="both", expand=True)
        task_columns.columnconfigure(0, weight=1)
        task_columns.columnconfigure(1, weight=1)

        ttk.Label(task_columns, text=T("All Tasks"), font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
        ttk.Label(task_columns, text=T("Pending Tasks"), font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky="w", pady=(0, 6))

        all_scroll = ttk.Scrollbar(task_columns, orient="vertical")
        pending_scroll = ttk.Scrollbar(task_columns, orient="vertical")
        all_h_scroll = ttk.Scrollbar(task_columns, orient="horizontal")
        pending_h_scroll = ttk.Scrollbar(task_columns, orient="horizontal")

        self.all_box = tk.Listbox(task_columns, height=14, exportselection=False, font=("Segoe UI", 11), yscrollcommand=all_scroll.set, xscrollcommand=all_h_scroll.set)
        self.pending_box = tk.Listbox(task_columns, height=14, exportselection=False, bg="#fffef5", font=("Segoe UI", 11), yscrollcommand=pending_scroll.set, xscrollcommand=pending_h_scroll.set)

        self.all_box.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 0))
        all_scroll.grid(row=1, column=0, sticky="ns", padx=(0, 0), pady=(0, 0))
        all_h_scroll.grid(row=2, column=0, sticky="ew", padx=(0, 6), pady=(0, 10))

        self.pending_box.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(0, 0))
        pending_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 0), pady=(0, 0))
        pending_h_scroll.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(0, 10))

        all_scroll.config(command=self.all_box.yview)
        pending_scroll.config(command=self.pending_box.yview)
        all_h_scroll.config(command=self.all_box.xview)
        pending_h_scroll.config(command=self.pending_box.xview)

        self.populate_lists(all_tasks=all_tasks, pending_tasks=pending_tasks)

        self.new_task_var = tk.StringVar()
        task_entry_row = ttk.Frame(main)
        task_entry_row.pack(fill="x", pady=(0, 10))
        new_task_label = ttk.Label(task_entry_row, text=T("New task"))
        new_task_label.pack(side="left", padx=(0, 6))
        self.new_task_entry = ttk.Entry(task_entry_row, textvariable=self.new_task_var)
        self.new_task_entry.bind("<Return>", lambda event: self.save_task())
        self.new_task_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(task_entry_row, text=T("Add Task"), command=self.save_task, style="Action.TButton", width=14).pack(side="left", padx=(6, 0))

        button_row = ttk.Frame(main)
        button_row.pack(fill="x", pady=(0, 8))
        ttk.Button(button_row, text=T("Edit"), command=self.edit_selected_task).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Mark Done"), command=self.mark_selected_done).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Delete Tasks"), command=self.delete_selected_task).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Print"), command=self.print_report).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Home"), command=self.go_home).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Close"), command=self.close_window).pack(side="left")

    def save_task(self):
        if self.plan is None:
            messagebox.showwarning(T("No task plan"), T("There is no active task plan to update."))
            return

        task = self.new_task_var.get().strip()
        if not task:
            self.new_task_entry.focus_set()
            self.new_task_entry.icursor(len(self.new_task_entry.get()))
            return

        self.plan.add_pending_task(task)
        if self.master_app and hasattr(self.master_app, "refresh_display"):
            self.master_app.refresh_display()
        self.populate_lists(all_tasks=self.plan.all_tasks, pending_tasks=self.plan.pending_tasks)
        self.new_task_var.set("")
        self.new_task_entry.focus_set()
        self.new_task_entry.icursor(0)

    def go_home(self):
        self.destroy()
        open_welcome_home()

    def print_report(self):
        client_name = self.plan.client_name if self.plan else self.master_app.client_name_var.get().strip() if self.master_app else "Client"
        title = T("Task Details - {client_name}", client_name=client_name)
        lines = [title, "", T("All Tasks") + ":"]
        lines.extend(self.plan.all_tasks if self.plan else [])
        lines.extend(["", T("Pending Tasks") + ":"])
        lines.extend(self.plan.pending_tasks if self.plan else [])
        print_report_document(title, lines)

    def populate_lists(self, all_tasks=None, pending_tasks=None):
        self.all_box.delete(0, tk.END)
        self.pending_box.delete(0, tk.END)

        tasks = list(all_tasks) if all_tasks is not None else []
        pending = list(pending_tasks) if pending_tasks is not None else []

        if tasks:
            for index, task in enumerate(tasks, start=1):
                self.all_box.insert(tk.END, format_task_entry(task, number=index))
        else:
            self.all_box.insert(tk.END, T("No tasks yet"))

        if pending:
            for index, task in enumerate(pending, start=1):
                self.pending_box.insert(tk.END, format_task_entry(task, number=index))
        else:
            self.pending_box.insert(tk.END, T("No pending tasks"))

    def close_window(self):
        self.destroy()
        if self.master_app is not None:
            try:
                self.master_app.deiconify()
            except Exception:
                pass

    def edit_selected_task(self):
        if self.plan is None:
            messagebox.showwarning(T("No task plan"), T("There is no active task plan to edit."))
            return

        selected = self.pending_box.curselection() or self.all_box.curselection()
        if not selected:
            messagebox.showwarning(T("No task selected"), T("Select a task first."))
            return

        source = self.pending_box if self.pending_box.curselection() else self.all_box
        raw_task = strip_task_number_prefix(source.get(selected[0]))
        new_text = simpledialog.askstring(T("Edit task"), T("Enter the updated task text:"), initialvalue=raw_task)
        if new_text is None:
            return

        updated_task = new_text.strip()
        if not updated_task:
            messagebox.showwarning(T("Invalid task"), T("Task text cannot be empty."))
            return

        if raw_task in self.plan.all_tasks:
            self.plan.all_tasks[self.plan.all_tasks.index(raw_task)] = updated_task
        if raw_task in self.plan.pending_tasks:
            self.plan.pending_tasks[self.plan.pending_tasks.index(raw_task)] = updated_task

        if self.master_app and hasattr(self.master_app, "refresh_display"):
            self.master_app.refresh_display()

        self.plan.sync_task_lists(all_tasks=self.plan.all_tasks, pending_tasks=self.plan.pending_tasks)
        self.populate_lists(all_tasks=self.plan.all_tasks, pending_tasks=self.plan.pending_tasks)

    def mark_selected_done(self):
        if self.plan is None:
            messagebox.showwarning(T("No task plan"), T("There is no active task plan to update."))
            return

        selected = self.pending_box.curselection()
        if not selected:
            messagebox.showwarning(T("No task selected"), T("Select a task from the pending list first."))
            return

        task = strip_task_number_prefix(self.pending_box.get(selected[0]))
        self.plan.complete_task(task)

        if self.master_app and hasattr(self.master_app, "refresh_display"):
            self.master_app.refresh_display()

        self.populate_lists(all_tasks=self.plan.all_tasks, pending_tasks=self.plan.pending_tasks)

    def delete_selected_task(self):
        if self.plan is None:
            messagebox.showwarning(T("No task plan"), T("There is no active task plan to update."))
            return

        selected = self.pending_box.curselection() or self.all_box.curselection()
        if not selected:
            messagebox.showwarning(T("No task selected"), T("Select a task first."))
            return

        source = self.pending_box if self.pending_box.curselection() else self.all_box
        task = strip_task_number_prefix(source.get(selected[0]))

        if task in self.plan.pending_tasks:
            self.plan.pending_tasks.remove(task)
        if task in self.plan.all_tasks:
            self.plan.all_tasks.remove(task)

        self.plan.sync_task_lists(all_tasks=self.plan.all_tasks, pending_tasks=self.plan.pending_tasks)

        if self.master_app and hasattr(self.master_app, "refresh_display"):
            self.master_app.refresh_display()

        self.populate_lists(all_tasks=self.plan.all_tasks, pending_tasks=self.plan.pending_tasks)


# Contract form used to capture legal and commercial details tied to a client record.
class ContractDetailsWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title(T("Contract Details"))
        self.geometry("680x520")
        self.minsize(500, 420)
        self.master_app = master
        self.manager = getattr(master, "client_manager", ClientManager("clients.json")) if master is not None else ClientManager("clients.json")

        self.client_name = ""
        if self.master_app is not None and hasattr(self.master_app, "client_name_var"):
            self.client_name = str(self.master_app.client_name_var.get() or "").strip()
        self.client = self._find_client(self.client_name)

        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        fields = [
            (T("Contract Number"), "contract_number"),
            (T("Starting Date"), "starting_date"),
            (T("Ending Date"), "ending_date"),
            (T("Commercial Registration Number"), "commercial_registration_number"),
            (T("Authorized Signature Name"), "authorized_signature_name"),
            (T("Rent Value"), "rent_value"),
        ]

        self.values = {}
        row_index = 0
        for label_text, key in fields:
            ttk.Label(main, text=label_text, font=("Segoe UI", 10, "bold")).grid(row=row_index, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
            var = tk.StringVar()
            self.values[key] = var
            if key in {"starting_date", "ending_date"}:
                date_frame = ttk.Frame(main)
                date_frame.grid(row=row_index, column=1, sticky="ew", pady=(0, 8))
                date_frame.columnconfigure(0, weight=1)
                ttk.Entry(date_frame, textvariable=var, width=32).grid(row=0, column=0, sticky="ew", padx=(0, 6))
                ttk.Button(date_frame, text="📅", width=3, command=lambda selected_key=key, entry_var=var: self._pick_date(selected_key, entry_var)).grid(row=0, column=1, sticky="e")
            else:
                ttk.Entry(main, textvariable=var, width=38).grid(row=row_index, column=1, sticky="ew", pady=(0, 8))
            row_index += 1

        ttk.Label(main, text=T("Currency Type"), font=("Segoe UI", 10, "bold")).grid(row=row_index, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
        currency_options = ["OMR", "USD", "AED", "SAR", "QAR", "BHD", "KWD", "EUR", "GBP", "JPY"]
        self.currency_var = tk.StringVar(value="OMR")
        self.currency_combo = ttk.Combobox(main, textvariable=self.currency_var, values=currency_options, state="readonly", width=35)
        self.currency_combo.grid(row=row_index, column=1, sticky="ew", pady=(0, 8))
        row_index += 1

        ttk.Label(main, text=T("Open Issues Requiring Attention"), font=("Segoe UI", 10, "bold")).grid(
            row=row_index, column=0, columnspan=2, sticky="w", pady=(10, 6)
        )
        self.open_issues_text = tk.Text(main, height=8, wrap="word", font=("Segoe UI", 10))
        self.open_issues_text.grid(row=row_index + 1, column=0, columnspan=2, sticky="nsew", pady=(0, 12))

        button_row = ttk.Frame(main)
        button_row.grid(row=row_index + 2, column=0, columnspan=2, sticky="e")
        ttk.Button(button_row, text=T("Save"), command=self.save_contract).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Close"), command=self.destroy).pack(side="left")

        self.bind("<Escape>", lambda event: self.destroy())
        self.load_existing_contract()

    def _find_client(self, client_name):
        if not client_name:
            return None
        self.manager.load_clients()
        return next((client for client in self.manager.clients if client.name.lower() == client_name.lower()), None)

    def _pick_date(self, key, var):
        date_value = var.get().strip()
        selected = pick_date(self, date_value)
        if selected:
            var.set(selected)

    def _collect_contract_details(self):
        details = {}
        for key, var in self.values.items():
            details[key] = var.get().strip()
        details["currency_type"] = (self.currency_var.get() or "OMR").strip() or "OMR"
        details["open_issues"] = self.open_issues_text.get("1.0", "end").strip()
        return details

    def load_existing_contract(self):
        if self.client is None or not isinstance(self.client.contract_details, dict):
            return

        for key, var in self.values.items():
            var.set(self.client.contract_details.get(key, ""))
        existing_currency = str(self.client.contract_details.get("currency_type") or "OMR").strip() or "OMR"
        if existing_currency not in self.currency_combo["values"]:
            existing_currency = "OMR"
        self.currency_var.set(existing_currency)
        self.open_issues_text.delete("1.0", tk.END)
        self.open_issues_text.insert("1.0", self.client.contract_details.get("open_issues", ""))

    def save_contract(self):
        if self.master_app is not None and hasattr(self.master_app, "client_name_var"):
            client_name = str(self.master_app.client_name_var.get() or "").strip()
            if not client_name or client_name == T("<New Client>"):
                messagebox.showwarning(T("No client selected"), T("Select a client from the list first."))
                return
        elif not self.client_name:
            messagebox.showwarning(T("No client selected"), T("Select a client from the list first."))
            return
        else:
            client_name = self.client_name

        self.manager.load_clients()
        client = next((item for item in self.manager.clients if item.name.lower() == client_name.lower()), None)
        if client is None:
            messagebox.showwarning(T("Client not found"), T("'{client_name}' was not found in the saved client list.", client_name=client_name))
            return

        client.contract_details = self._collect_contract_details()
        self.manager.save_clients()

        if self.master_app is not None and hasattr(self.master_app, "refresh_client_combo"):
            self.master_app.refresh_client_combo()

        messagebox.showinfo(T("Client saved"), T("'{name}' was saved successfully.", name=client.name))
        self.destroy()


# Report preview dialog showing a generated client log without leaving the UI.
class ClientLogPreviewWindow(tk.Toplevel):
    def __init__(self, master=None, report_text=""):
        super().__init__(master)
        self.title(T("Client Overview Preview"))
        self.geometry("900x600")
        self.minsize(700, 400)
        self.transient(master)
        self.grab_set()

        text_widget = tk.Text(self, wrap="word", font=("Segoe UI", 10), padx=10, pady=10)
        text_widget.insert("1.0", report_text)
        text_widget.configure(state="disabled")
        text_widget.pack(fill="both", expand=True, padx=12, pady=(12, 8))

        button_row = ttk.Frame(self)
        button_row.pack(fill="x", padx=12, pady=(0, 12))
        button_row.columnconfigure(0, weight=1)
        ttk.Button(button_row, text=T("Close Preview"), command=self.destroy).grid(row=0, column=1, sticky="e")

        self.protocol("WM_DELETE_WINDOW", self.destroy)


# Payment summary window that combines contract status with the client's transaction history.
class ClientPaymentReportWindow(tk.Toplevel):
    def __init__(self, master=None, client_name=""):
        super().__init__(master)
        self.previous_window = master
        self.title(T("Client Payment Report"))
        self.geometry("900x620")
        self.minsize(720, 420)
        self.master_app = master
        self.protocol("WM_DELETE_WINDOW", self.go_back)
        self.client_name = str(client_name or "").strip()
        self.manager = getattr(master, "client_manager", ClientManager("clients.json")) if master is not None else ClientManager("clients.json")
        self.manager.load_clients()

        self.client = self._find_client(self.client_name) if self.client_name else None
        if self.client is None and self.master_app is not None and hasattr(self.master_app, "client_name_var"):
            determined = str(self.master_app.client_name_var.get() or "").strip()
            self.client_name = determined
            self.client = self._find_client(determined)

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        selector_row = ttk.Frame(main)
        selector_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        selector_row.columnconfigure(1, weight=1)

        ttk.Label(selector_row, text=T("Client Name")).pack(side="left", padx=(0, 8))
        self.client_selector_var = tk.StringVar(value=self.client_name or T("<New Client>"))
        self.client_selector = ttk.Combobox(
            selector_row,
            textvariable=self.client_selector_var,
            values=self._client_combo_values(),
            state="normal",
            width=44,
        )
        self.client_selector.pack(side="left", fill="x", expand=True)
        self.client_selector.bind("<<ComboboxSelected>>", self._handle_client_selection)
        self.client_selector_var.trace_add("write", self._handle_client_selection)

        self.contract_status_label = ttk.Label(
            main,
            text=f"{T('Contract Period Status')}: {self._contract_status_text()}",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self.contract_status_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.text_widget = tk.Text(main, wrap="word", font=("Segoe UI", 10), padx=10, pady=10)
        self.text_widget.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self._refresh_report_view()

        button_row = ttk.Frame(main)
        button_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(button_row, text=T("Print"), command=self.print_report).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Save Log"), command=self.save_report).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Back"), command=self.go_back).pack(side="left")
        main.rowconfigure(2, weight=1)

    def go_back(self):
        close_popup_and_return(self)

    def _client_combo_values(self):
        self.manager.load_clients()
        names = sorted({str(client.name).strip() for client in self.manager.clients if getattr(client, "name", "").strip()})
        return [T("<New Client>")] + names

    def _handle_client_selection(self, *_args):
        self._sync_selected_client()
        self._refresh_report_view()

    def _sync_selected_client(self):
        raw_name = str(self.client_selector_var.get() or "").strip()
        if not raw_name or raw_name == T("<New Client>"):
            self.client_name = ""
            self.client = None
            return

        self.client_name = raw_name
        self.client = self._find_client(raw_name)

    def _refresh_report_view(self):
        self._sync_selected_client()
        self.contract_status_label.configure(text=f"{T('Contract Period Status')}: {self._contract_status_text()}")
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", self.build_report_text())
        self.text_widget.configure(state="disabled")

    def _find_client(self, client_name):
        if not client_name:
            return None
        self.manager.load_clients()
        return next((client for client in self.manager.clients if client.name.lower() == client_name.lower()), None)

    def _contract_status_text(self):
        if self.client is None:
            return "N/A"

        contract_details = self.client.contract_details or {}
        contract_start = str(contract_details.get("starting_date") or "").strip()
        contract_end = str(contract_details.get("ending_date") or "").strip()
        current_date = datetime.now().strftime("%d-%m-%Y")
        status = "Active"
        if contract_start and contract_end:
            try:
                start_dt = datetime.strptime(contract_start, "%d-%m-%Y")
                end_dt = datetime.strptime(contract_end, "%d-%m-%Y")
                today_dt = datetime.strptime(current_date, "%d-%m-%Y")
                if today_dt < start_dt:
                    status = "Not Started"
                elif today_dt > end_dt:
                    status = "Expired"
            except ValueError:
                status = "Pending evaluation"
        elif contract_start and not contract_end:
            status = "In progress"
        elif not contract_start and contract_end:
            status = "Pending start date"

        return status

    def build_report_text(self):
        if self.client is None:
            return "Client Payment Report\n\nNo client selected."
        return build_client_payment_report_text(self.client.name, self.manager)

    def print_report(self):
        if self.client is None:
            messagebox.showwarning(T("No client selected"), T("Select a client from the list first."))
            return
        print_report_document(f"Client Payment Report - {self.client.name}", self.build_report_text().splitlines())

    def save_report(self):
        if self.client is None:
            messagebox.showwarning(T("No client selected"), T("Select a client from the list first."))
            return

        default_dir = resolve_log_output_dir("clients_logs")
        default_path = default_dir / f"{self.client.name.replace(' ', '_')}_payment_report.txt"
        destination = filedialog.asksaveasfilename(
            title=T("Select file path"),
            initialfile=default_path.name,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=str(default_dir),
        )
        if not destination:
            return

        try:
            Path(destination).write_text(self.build_report_text(), encoding="utf-8")
            messagebox.showinfo(T("Save Log"), f"Saved: {destination}")
        except OSError as exc:
            messagebox.showerror(T("Save Log"), f"Unable to save report: {exc}")


class ClientTransactionsWindow(tk.Toplevel):
    PAYMENT_METHOD_CHOICES = ("Cash", "Cheque", "Bank Transaction")

    def __init__(self, master=None, client_name=""):
        super().__init__(master)
        self.title(T("Client Transactions"))
        self.geometry("980x560")
        self.minsize(780, 420)
        self.master_app = master
        self.client_name = str(client_name or "").strip()
        self.manager = getattr(master, "client_manager", ClientManager("clients.json")) if master is not None else ClientManager("clients.json")
        self.manager.load_clients()

        self.client = self._find_client(self.client_name) if self.client_name else None
        if self.client is None and self.master_app is not None and hasattr(self.master_app, "client_name_var"):
            determined = str(self.master_app.client_name_var.get() or "").strip()
            self.client_name = determined
            self.client = self._find_client(determined)

        self.status_checkbuttons = {}
        self.status_vars = {}
        self.method_comboboxes = {}
        self.method_vars = {}
        self.cheque_entries = {}
        self.cheque_vars = {}
        self.bank_transaction_entries = {}
        self.bank_transaction_vars = {}
        self.amount_entries = {}
        self.amount_vars = {}
        self.due_date_entries = {}
        self.due_date_vars = {}
        self.bank_name_entries = {}
        self.bank_name_vars = {}
        self.due_date_buttons = {}
        self.month_comboboxes = {}
        self.month_vars = {}
        self.month_options = self._build_month_options()

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 10))

        header_fields = ttk.Frame(header)
        header_fields.pack(fill="x")
        header_fields.columnconfigure(1, weight=1)

        ttk.Label(header_fields, text=f"{T('Client')}:", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.client_selector_var = tk.StringVar(value=self.client_name or "")
        self.client_selector = ttk.Combobox(
            header_fields,
            textvariable=self.client_selector_var,
            values=self._list_client_names(),
            state="readonly",
            width=28,
        )
        self.client_selector.grid(row=0, column=1, sticky="ew")
        self.client_selector.bind("<<ComboboxSelected>>", self._switch_client_for_transactions)

        columns = ("month", "status", "amount", "method", "cheque", "due_date", "bank", "bank_transaction_detail")
        self.tree = ttk.Treeview(main, columns=columns, show="headings", height=14)
        for column, title in zip(columns, [T("Month"), T("Status"), T("Amount"), T("Payment Method"), T("Cheque Number"), T("Due Date"), T("Bank Name"), T("Bank Transaction Details")]):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=120, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Configure>", lambda event: (
            self._position_status_checkbuttons(),
            self._position_method_comboboxes(),
            self._position_cheque_entries(),
            self._position_bank_transaction_entries(),
            self._position_amount_entries(),
            self._position_due_date_entries(),
            self._position_due_date_buttons(),
            self._position_bank_name_entries(),
            self._position_month_comboboxes(),
        ))

        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=(8, 0))
        ttk.Button(controls, text=T("Add Month"), command=self.add_transaction_row).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text=T("Save Transactions"), command=self.save_transactions).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text=T("Back"), command=self.go_back).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text=T("Home"), command=self.go_home).pack(side="left")

        self.refresh_view()

    def go_back(self):
        close_popup_and_return(self)

    def _list_client_names(self):
        self.manager.load_clients()
        return [client.name for client in self.manager.clients if getattr(client, "name", "").strip()]

    def _find_client(self, client_name):
        if not client_name:
            return None
        self.manager.load_clients()
        return next((client for client in self.manager.clients if client.name.lower() == client_name.lower()), None)

    def _switch_client_for_transactions(self, event=None):
        selected_name = str(self.client_selector_var.get() or "").strip()
        if not selected_name:
            return

        self.client_name = selected_name
        self.client = self._find_client(selected_name)
        self.month_options = self._build_month_options()
        self.refresh_view()

    def go_home(self):
        self.destroy()
        open_welcome_home()

    def _build_month_options(self):
        if self.client is None:
            return []

        contract_details = getattr(self.client, "contract_details", {}) or {}
        start_date = str(contract_details.get("starting_date") or "").strip()
        end_date = str(contract_details.get("ending_date") or "").strip()
        months = generate_contract_months(start_date, end_date)
        if months:
            return months
        return []

    def _normalize_payment_method(self, value):
        if value is None:
            return "Cash"

        normalized = str(value).strip()
        if not normalized:
            return "Cash"

        lookup = {choice.lower(): choice for choice in self.PAYMENT_METHOD_CHOICES}
        if normalized.lower() in lookup:
            return lookup[normalized.lower()]

        for choice in self.PAYMENT_METHOD_CHOICES:
            if normalized.lower() in choice.lower():
                return choice

        return "Cash"

    def _is_payment_completed(self, entry):
        status = str(entry.get("status", "") or "").strip().lower()
        return status in {"paid", "completed", "complete", "success", "successful", "yes", "true", "1"}

    def _position_status_checkbuttons(self):
        for row_id, checkbutton in list(self.status_checkbuttons.items()):
            if not self.tree.exists(row_id):
                checkbutton.destroy()
                self.status_checkbuttons.pop(row_id, None)
                self.status_vars.pop(row_id, None)
                continue

            try:
                x, y, width, height = self.tree.bbox(row_id, "status")
            except Exception:
                continue

            if width <= 0:
                continue

            checkbutton.place(x=x + 4, y=y + 2, width=max(18, width - 8), height=max(18, height - 4))

    def _position_method_comboboxes(self):
        for row_id, combobox in list(self.method_comboboxes.items()):
            if not self.tree.exists(row_id):
                combobox.destroy()
                self.method_comboboxes.pop(row_id, None)
                self.method_vars.pop(row_id, None)
                continue

            try:
                x, y, width, height = self.tree.bbox(row_id, "method")
            except Exception:
                continue

            if width <= 0:
                continue

            combobox.place(x=x + 2, y=y + 2, width=max(120, width - 6), height=max(22, height - 4))

    def _position_cheque_entries(self):
        for row_id, entry_widget in list(self.cheque_entries.items()):
            if not self.tree.exists(row_id):
                entry_widget.destroy()
                self.cheque_entries.pop(row_id, None)
                self.cheque_vars.pop(row_id, None)
                continue

            try:
                x, y, width, height = self.tree.bbox(row_id, "cheque")
            except Exception:
                continue

            if width <= 0:
                continue

            entry_widget.place(x=x + 2, y=y + 2, width=max(90, width - 6), height=max(22, height - 4))

    def _position_bank_transaction_entries(self):
        for row_id, entry_widget in list(self.bank_transaction_entries.items()):
            if not self.tree.exists(row_id):
                entry_widget.destroy()
                self.bank_transaction_entries.pop(row_id, None)
                self.bank_transaction_vars.pop(row_id, None)
                continue

            try:
                x, y, width, height = self.tree.bbox(row_id, "bank_transaction_detail")
            except Exception:
                continue

            if width <= 0:
                continue

            entry_widget.place(x=x + 2, y=y + 2, width=max(110, width - 6), height=max(22, height - 4))

    def _position_amount_entries(self):
        for row_id, entry_widget in list(self.amount_entries.items()):
            if not self.tree.exists(row_id):
                entry_widget.destroy()
                self.amount_entries.pop(row_id, None)
                self.amount_vars.pop(row_id, None)
                continue

            try:
                x, y, width, height = self.tree.bbox(row_id, "amount")
            except Exception:
                continue

            if width <= 0:
                continue

            entry_widget.place(x=x + 2, y=y + 2, width=max(90, width - 6), height=max(22, height - 4))

    def _position_due_date_entries(self):
        for row_id, entry_widget in list(self.due_date_entries.items()):
            if not self.tree.exists(row_id):
                entry_widget.destroy()
                self.due_date_entries.pop(row_id, None)
                self.due_date_vars.pop(row_id, None)
                continue

            try:
                x, y, width, height = self.tree.bbox(row_id, "due_date")
            except Exception:
                continue

            if width <= 0:
                continue

            entry_widget.place(x=x + 2, y=y + 2, width=max(92, width - 34), height=max(22, height - 4))

    def _position_due_date_buttons(self):
        for row_id, button_widget in list(self.due_date_buttons.items()):
            if not self.tree.exists(row_id):
                button_widget.destroy()
                self.due_date_buttons.pop(row_id, None)
                continue

            try:
                x, y, width, height = self.tree.bbox(row_id, "due_date")
            except Exception:
                continue

            if width <= 0:
                continue

            button_widget.place(x=x + max(92, width - 28), y=y + 2, width=28, height=max(22, height - 4))

    def _position_bank_name_entries(self):
        for row_id, entry_widget in list(self.bank_name_entries.items()):
            if not self.tree.exists(row_id):
                entry_widget.destroy()
                self.bank_name_entries.pop(row_id, None)
                self.bank_name_vars.pop(row_id, None)
                continue

            try:
                x, y, width, height = self.tree.bbox(row_id, "bank")
            except Exception:
                continue

            if width <= 0:
                continue

            entry_widget.place(x=x + 2, y=y + 2, width=max(110, width - 6), height=max(22, height - 4))

    def _position_month_comboboxes(self):
        for row_id, combobox in list(self.month_comboboxes.items()):
            if not self.tree.exists(row_id):
                combobox.destroy()
                self.month_comboboxes.pop(row_id, None)
                self.month_vars.pop(row_id, None)
                continue

            try:
                x, y, width, height = self.tree.bbox(row_id, "month")
            except Exception:
                continue

            if width <= 0:
                continue

            combobox.place(x=x + 2, y=y + 2, width=max(110, width - 6), height=max(22, height - 4))

    def _get_month_order_index(self, month_value):
        if not month_value:
            return -1
        if not self.month_options:
            return -1
        try:
            return self.month_options.index(month_value)
        except ValueError:
            return -1

    def _can_complete_payment(self, entry):
        if not entry:
            return False

        month = str(entry.get("month", "") or "").strip()
        amount = str(entry.get("amount", "") or "").strip()
        payment_method = self._normalize_payment_method(entry.get("payment_method", "Cash"))
        due_date = str(entry.get("due_date", "") or "").strip()
        cheque_number = str(entry.get("cheque_number", "") or "").strip()
        bank_detail = str(entry.get("bank_transaction_details", "") or "").strip()

        if not month or not amount or not due_date:
            return False

        if payment_method == "Cheque":
            if not cheque_number:
                return False
            return bool(cheque_number)
        elif payment_method == "Bank Transaction":
            if not bank_detail:
                return False
            return bool(bank_detail)

        current_index = self._get_month_order_index(month)
        if current_index <= 0:
            return True

        previous_month = self.month_options[current_index - 1] if current_index - 1 >= 0 else ""
        if not previous_month:
            return True

        for candidate in (getattr(self.client, "transactions", []) or []):
            if str(candidate.get("month", "") or "").strip() != previous_month:
                continue
            if str(candidate.get("status", "") or "").strip().lower() not in {"paid", "completed", "complete", "success", "successful"}:
                return False
            break
        else:
            return False

        return True

    def _toggle_status(self, row_id, entry, var):
        completed = bool(var.get())
        if not completed:
            entry["status"] = "Pending"
            self.tree.set(row_id, "status", "Pending")
            return

        if not self._can_complete_payment(entry):
            var.set(False)
            entry["status"] = "Pending"
            self.tree.set(row_id, "status", "Pending")
            prior_month = self._get_previous_month(entry.get("month", ""))
            if prior_month:
                messagebox.showwarning(T("Outstanding payment"), T("Complete the previous month payment for '{month}' before marking this payment as paid.", month=prior_month))
            else:
                messagebox.showwarning(T("Incomplete payment"), T("Complete the required payment details before marking this month as paid."))
            return

        entry["status"] = "Paid"
        self.tree.set(row_id, "status", "Paid")

    def _coerce_due_date_for_month(self, month_value, due_date_value):
        month_text = str(month_value or "").strip()
        if not month_text:
            return str(due_date_value or "").strip()

        try:
            month_start = datetime.strptime(f"{month_text}-01", "%Y-%m-%d")
        except ValueError:
            return str(due_date_value or "").strip()

        last_day = calendar.monthrange(month_start.year, month_start.month)[1]
        month_end = datetime(month_start.year, month_start.month, last_day).strftime("%d-%m-%Y")

        value = str(due_date_value or "").strip()
        if not value:
            return month_end

        try:
            parsed = datetime.strptime(value, "%d-%m-%Y")
        except ValueError:
            try:
                parsed = datetime.fromisoformat(value)
                parsed = parsed if parsed else datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return month_end

        if parsed.year == month_start.year and parsed.month == month_start.month:
            return parsed.strftime("%d-%m-%Y")
        return month_end

    def _get_previous_month(self, month_value):
        month = str(month_value or "").strip()
        current_index = self._get_month_order_index(month)
        if current_index <= 0 or not self.month_options:
            return ""
        return self.month_options[current_index - 1]

    def _update_month(self, row_id, entry, var):
        entry["month"] = str(var.get() or "").strip()
        self.tree.set(row_id, "month", entry["month"])

        coerced_due_date = self._coerce_due_date_for_month(entry["month"], entry.get("due_date", ""))
        if coerced_due_date != str(entry.get("due_date", "") or "").strip():
            entry["due_date"] = coerced_due_date
            self.tree.set(row_id, "due_date", coerced_due_date)
            if row_id in self.due_date_vars:
                self.due_date_vars[row_id].set(coerced_due_date)

    def _update_payment_method(self, row_id, entry, var):
        entry["payment_method"] = self._normalize_payment_method(var.get())
        self.tree.set(row_id, "method", entry["payment_method"])

        cheque_entry = self.cheque_entries.get(row_id)
        if cheque_entry is not None:
            if entry["payment_method"] == "Cheque":
                cheque_entry.configure(state="normal")
            else:
                if entry.get("cheque_number", "").strip():
                    entry["cheque_number"] = ""
                    self.cheque_vars[row_id].set("")
                cheque_entry.configure(state="disabled")

        bank_detail_entry = self.bank_transaction_entries.get(row_id)
        if bank_detail_entry is not None:
            if entry["payment_method"] == "Bank Transaction":
                bank_detail_entry.configure(state="normal")
            else:
                if entry.get("bank_transaction_details", "").strip():
                    entry["bank_transaction_details"] = ""
                    self.bank_transaction_vars[row_id].set("")
                bank_detail_entry.configure(state="disabled")

    def refresh_view(self):
        self.month_options = self._build_month_options()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row_id, checkbutton in list(self.status_checkbuttons.items()):
            checkbutton.destroy()
        self.status_checkbuttons.clear()
        self.status_vars.clear()

        for row_id, combobox in list(self.method_comboboxes.items()):
            combobox.destroy()
        self.method_comboboxes.clear()
        self.method_vars.clear()

        for row_id, entry_widget in list(self.cheque_entries.items()):
            entry_widget.destroy()
        self.cheque_entries.clear()
        self.cheque_vars.clear()

        for row_id, entry_widget in list(self.bank_transaction_entries.items()):
            entry_widget.destroy()
        self.bank_transaction_entries.clear()
        self.bank_transaction_vars.clear()

        for row_id, entry_widget in list(self.amount_entries.items()):
            entry_widget.destroy()
        self.amount_entries.clear()
        self.amount_vars.clear()

        for row_id, entry_widget in list(self.due_date_entries.items()):
            entry_widget.destroy()
        self.due_date_entries.clear()
        self.due_date_vars.clear()

        for row_id, button_widget in list(self.due_date_buttons.items()):
            button_widget.destroy()
        self.due_date_buttons.clear()

        for row_id, entry_widget in list(self.bank_name_entries.items()):
            entry_widget.destroy()
        self.bank_name_entries.clear()
        self.bank_name_vars.clear()

        for row_id, combobox in list(self.month_comboboxes.items()):
            combobox.destroy()
        self.month_comboboxes.clear()
        self.month_vars.clear()

        if self.client is None:
            self.tree.insert("", "end", values=(T("No client selected"), "", "", "", "", "", ""))
            return

        transactions = list(getattr(self.client, "transactions", []) or [])
        if not transactions:
            self.tree.insert("", "end", values=(T("No payments yet"), "", "", "", "", "", ""))
            return

        for entry in transactions:
            month_value = str(entry.get("month", "") or "").strip()
            if self.month_options and month_value not in self.month_options:
                month_value = month_value or self.month_options[0]
            if not month_value:
                month_value = self.month_options[0] if self.month_options else ""

            row_id = self.tree.insert(
                "",
                "end",
                values=(
                    month_value,
                    "",
                    str(entry.get("amount", "")),
                    self._normalize_payment_method(entry.get("payment_method", "Cash")),
                    str(entry.get("cheque_number", "")),
                    str(entry.get("due_date", "")),
                    str(entry.get("bank_name", "")),
                    str(entry.get("bank_transaction_details", "")),
                ),
            )

            month_var = tk.StringVar(value=month_value)
            self.month_vars[row_id] = month_var
            month_combo = ttk.Combobox(
                self.tree,
                textvariable=month_var,
                values=list(self.month_options) if self.month_options else [month_value],
                state="readonly" if self.month_options else "normal",
                width=12,
            )
            month_combo.bind(
                "<<ComboboxSelected>>",
                lambda event, current_row=row_id, current_entry=entry, current_var=month_var: self._update_month(current_row, current_entry, current_var),
            )
            self.month_comboboxes[row_id] = month_combo

            checkbox_var = tk.BooleanVar(value=self._is_payment_completed(entry))
            self.status_vars[row_id] = checkbox_var
            checkbutton = tk.Checkbutton(
                self.tree,
                variable=checkbox_var,
                command=lambda current_row=row_id, current_entry=entry, current_var=checkbox_var: self._toggle_status(current_row, current_entry, current_var),
                bd=0,
                highlightthickness=0,
                padx=0,
                pady=0,
            )
            self.status_checkbuttons[row_id] = checkbutton

            method_var = tk.StringVar(value=self._normalize_payment_method(entry.get("payment_method", "Cash")))
            self.method_vars[row_id] = method_var
            combobox = ttk.Combobox(
                self.tree,
                textvariable=method_var,
                values=list(self.PAYMENT_METHOD_CHOICES),
                state="readonly",
                width=16,
            )
            combobox.bind(
                "<<ComboboxSelected>>",
                lambda event, current_row=row_id, current_entry=entry, current_var=method_var: self._update_payment_method(current_row, current_entry, current_var),
            )
            self.method_comboboxes[row_id] = combobox

            amount_var = tk.StringVar(value=str(entry.get("amount", "")))
            self.amount_vars[row_id] = amount_var
            amount_entry = ttk.Entry(self.tree, textvariable=amount_var, width=10)
            amount_entry.bind("<FocusOut>", lambda event, current_row=row_id, current_entry=entry, current_var=amount_var: self._update_amount(current_row, current_entry, current_var))
            self.amount_entries[row_id] = amount_entry

            due_date_var = tk.StringVar(value=str(entry.get("due_date", "")))
            self.due_date_vars[row_id] = due_date_var
            due_date_entry = ttk.Entry(self.tree, textvariable=due_date_var, width=12, state="readonly")
            due_date_entry.bind("<FocusOut>", lambda event, current_row=row_id, current_entry=entry, current_var=due_date_var: self._update_due_date(current_row, current_entry, current_var))
            self.due_date_entries[row_id] = due_date_entry
            due_date_button = ttk.Button(self.tree, text="📅", width=3, command=lambda current_row=row_id, current_var=due_date_var, current_entry=entry: self._pick_due_date(current_row, current_var, current_entry))
            self.due_date_buttons[row_id] = due_date_button

            bank_name_var = tk.StringVar(value=str(entry.get("bank_name", "")))
            self.bank_name_vars[row_id] = bank_name_var
            bank_name_entry = ttk.Entry(self.tree, textvariable=bank_name_var, width=14)
            bank_name_entry.bind("<FocusOut>", lambda event, current_row=row_id, current_entry=entry, current_var=bank_name_var: self._update_bank_name(current_row, current_entry, current_var))
            self.bank_name_entries[row_id] = bank_name_entry

            cheque_var = tk.StringVar(value=str(entry.get("cheque_number", "")))
            self.cheque_vars[row_id] = cheque_var
            cheque_entry = ttk.Entry(self.tree, textvariable=cheque_var, width=12)
            cheque_entry.bind("<FocusOut>", lambda event, current_row=row_id, current_entry=entry, current_var=cheque_var: self._update_cheque_number(current_row, current_entry, current_var))
            self.cheque_entries[row_id] = cheque_entry
            if self._normalize_payment_method(entry.get("payment_method", "Cash")) != "Cheque":
                cheque_entry.configure(state="disabled")

            bank_transaction_var = tk.StringVar(value=str(entry.get("bank_transaction_details", "")))
            self.bank_transaction_vars[row_id] = bank_transaction_var
            bank_transaction_entry = ttk.Entry(self.tree, textvariable=bank_transaction_var, width=14)
            bank_transaction_entry.bind("<FocusOut>", lambda event, current_row=row_id, current_entry=entry, current_var=bank_transaction_var: self._update_bank_transaction_details(current_row, current_entry, current_var))
            self.bank_transaction_entries[row_id] = bank_transaction_entry
            if self._normalize_payment_method(entry.get("payment_method", "Cash")) != "Bank Transaction":
                bank_transaction_entry.configure(state="disabled")

        self._position_status_checkbuttons()
        self._position_method_comboboxes()
        self._position_amount_entries()
        self._position_due_date_entries()
        self._position_due_date_buttons()
        self._position_bank_name_entries()
        self._position_cheque_entries()
        self._position_bank_transaction_entries()
        self._position_month_comboboxes()

    def _update_amount(self, row_id, entry, var):
        value = str(var.get() or "").strip()
        try:
            if value:
                float(value)
            entry["amount"] = value
        except ValueError:
            entry["amount"] = ""
            var.set("")
            messagebox.showwarning(T("Invalid amount"), T("Please enter a valid numeric amount."))

    def _pick_due_date(self, row_id, var, entry=None):
        selected = pick_date(self, var.get())
        if not selected:
            return
        current_month = str((entry or {}).get("month", "") or "").strip()
        normalized = self._coerce_due_date_for_month(current_month, selected)
        var.set(normalized)
        self.tree.set(row_id, "due_date", normalized)
        if entry is not None:
            entry["due_date"] = normalized
        if row_id in self.due_date_vars:
            self.due_date_vars[row_id].set(normalized)

    def _update_due_date(self, row_id, entry, var):
        value = str(var.get() or "").strip()
        normalized = self._coerce_due_date_for_month(entry.get("month", ""), value)
        entry["due_date"] = normalized
        self.tree.set(row_id, "due_date", normalized)
        var.set(normalized)

    def _update_bank_name(self, row_id, entry, var):
        entry["bank_name"] = str(var.get() or "").strip()

    def _update_cheque_number(self, row_id, entry, var):
        entry["cheque_number"] = str(var.get() or "").strip()

    def _update_bank_transaction_details(self, row_id, entry, var):
        entry["bank_transaction_details"] = str(var.get() or "").strip()

    def _next_month_for_new_row(self):
        if not self.month_options:
            return ""

        saved_months = [
            str(item.get("month", "") or "").strip()
            for item in (getattr(self.client, "transactions", []) or [])
            if str(item.get("month", "") or "").strip()
        ]
        if not saved_months:
            return self.month_options[0]

        contract_end_month = self.month_options[-1]
        existing_months = {month for month in saved_months if month in self.month_options}
        if contract_end_month in existing_months:
            return contract_end_month

        last_month = ""
        last_dt = None
        for month_value in saved_months:
            if month_value not in self.month_options:
                continue
            try:
                candidate = datetime.strptime(f"{month_value}-01", "%Y-%m-%d")
            except ValueError:
                continue
            if last_dt is None or candidate > last_dt:
                last_dt = candidate
                last_month = month_value

        if last_dt is None:
            return self.month_options[0]

        current_index = self.month_options.index(last_month) if last_month in self.month_options else -1
        if current_index >= len(self.month_options) - 1:
            return contract_end_month

        return self.month_options[current_index + 1]

    def add_transaction_row(self):
        if self.client is None:
            messagebox.showwarning(T("No client selected"), T("Select a client from the list first."))
            return

        if self.month_options:
            existing_months = {
                str(item.get("month", "") or "").strip()
                for item in (getattr(self.client, "transactions", []) or [])
                if str(item.get("month", "") or "").strip()
            }
            if self.month_options[-1] in existing_months:
                return

        month_value = self._next_month_for_new_row()
        self.client.transactions.append({
            "month": month_value,
            "status": "Pending",
            "amount": "",
            "payment_method": "Cash",
            "cheque_number": "",
            "due_date": "",
            "bank_name": "",
            "bank_transaction_details": "",
        })
        self.refresh_view()

    def save_transactions(self):
        if self.client is None:
            messagebox.showwarning(T("No client selected"), T("Select a client from the list first."))
            return

        completed_rows = []
        for row_id, entry in zip(self.tree.get_children(), self.client.transactions):
            if row_id in self.month_vars:
                entry["month"] = str(self.month_vars[row_id].get() or "").strip()
            if row_id in self.status_vars:
                entry["status"] = "Paid" if self.status_vars[row_id].get() else "Pending"
            if row_id in self.amount_vars:
                entry["amount"] = str(self.amount_vars[row_id].get() or "").strip()
            if row_id in self.method_vars:
                entry["payment_method"] = self._normalize_payment_method(self.method_vars[row_id].get())
            if row_id in self.cheque_vars:
                entry["cheque_number"] = str(self.cheque_vars[row_id].get() or "").strip()
            if row_id in self.due_date_vars:
                entry["due_date"] = str(self.due_date_vars[row_id].get() or "").strip()
            if row_id in self.bank_name_vars:
                entry["bank_name"] = str(self.bank_name_vars[row_id].get() or "").strip()
            if row_id in self.bank_transaction_vars:
                entry["bank_transaction_details"] = str(self.bank_transaction_vars[row_id].get() or "").strip()

            if entry.get("status", "").lower() == "paid" and self._can_complete_payment(entry):
                completed_rows.append(entry)

        self.manager.load_clients()
        for existing in self.manager.clients:
            if existing.name.lower() == self.client.name.lower():
                existing.transactions = [
                    {
                        "month": str(item.get("month", "") or "").strip(),
                        "status": str(item.get("status", "") or "").strip(),
                        "amount": str(item.get("amount", "") or "").strip(),
                        "payment_method": str(item.get("payment_method", "") or "").strip(),
                        "cheque_number": str(item.get("cheque_number", "") or "").strip(),
                        "due_date": str(item.get("due_date", "") or "").strip(),
                        "bank_name": str(item.get("bank_name", "") or "").strip(),
                        "bank_transaction_details": str(item.get("bank_transaction_details", "") or "").strip(),
                    }
                    for item in self.client.transactions
                ]
                break
        self.manager.save_clients()

        if completed_rows:
            month_name = str(completed_rows[-1].get("month", "") or "").strip() or "this month"
            messagebox.showinfo(T("Payment completed"), f"Payment for {month_name} has been marked as successfully completed.")

        messagebox.showinfo(T("Transactions saved"), T("Client payment transactions were updated successfully."))
        self.refresh_view()


class ExportClientsLogWindow(tk.Toplevel):
    def __init__(self, master=None, manager=None):
        super().__init__(master)
        self.title(T("Export Clients Log"))
        self.geometry("560x180")
        self.minsize(420, 150)
        self.manager = manager or ClientManager("clients.json")

        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        default_dir = resolve_log_output_dir("clients_logs")
        default_path = default_dir / "clients_log.txt"

        ttk.Label(main, text=T("Select file path")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        self.path_var = tk.StringVar(value=str(default_path))
        self.path_entry = ttk.Entry(main, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Button(main, text=T("Browse"), command=self.choose_file_path).grid(row=0, column=2, sticky="ew", padx=(8, 0), pady=(0, 8))

        action_row = ttk.Frame(main)
        action_row.grid(row=1, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(action_row, text=T("Preview"), command=self.preview_report).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text=T("Save Log"), command=self.save_report).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text=T("Home"), command=self.go_home).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text=T("Cancel"), command=self.destroy).pack(side="left")

    def go_home(self):
        self.destroy()
        open_welcome_home()

    def choose_file_path(self):
        default_dir = resolve_log_output_dir("clients_logs")
        initial = self.path_var.get().strip() or str(default_dir / "clients_log.txt")
        selected = filedialog.asksaveasfilename(
            title=T("Select file path"),
            initialfile=Path(initial).name or "clients_log.txt",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=str(Path(initial).parent if Path(initial).parent.exists() else default_dir),
        )
        if selected:
            self.path_var.set(selected)

    def build_report_text(self):
        return build_clients_report_text(self.manager.file_path if hasattr(self.manager, "file_path") else "clients.json")

    def preview_report(self):
        report = self.build_report_text()
        ClientLogPreviewWindow(self, report)

    def save_report(self):
        target_path = self.path_var.get().strip()
        if not target_path:
            messagebox.showwarning(T("Select file path"), T("Select file path"))
            return

        destination = Path(target_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        report = append_report_footer(self.build_report_text().splitlines())
        destination.write_text("\n".join(report) + "\n", encoding="utf-8")
        messagebox.showinfo(T("Save Log"), f"Saved: {destination}")
        self.destroy()


class ExportTaskLogWindow(tk.Toplevel):
    def __init__(self, master=None, plan=None):
        super().__init__(master)
        self.title(T("Export Task Log"))
        self.geometry("560x180")
        self.minsize(420, 150)
        self.plan = plan or getattr(master, "plan", None) if master is not None else None

        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        default_dir = resolve_log_output_dir("tasks_logs")
        default_path = default_dir / "tasks_log.txt"

        ttk.Label(main, text=T("Select file path")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        self.path_var = tk.StringVar(value=str(default_path))
        self.path_entry = ttk.Entry(main, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Button(main, text=T("Browse"), command=self.choose_file_path).grid(row=0, column=2, sticky="ew", padx=(8, 0), pady=(0, 8))

        action_row = ttk.Frame(main)
        action_row.grid(row=1, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(action_row, text=T("Preview"), command=self.preview_report).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text=T("Save Log"), command=self.save_report).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text=T("Home"), command=self.go_home).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text=T("Cancel"), command=self.destroy).pack(side="left")

    def go_home(self):
        self.destroy()
        open_welcome_home()

    def choose_file_path(self):
        default_dir = resolve_log_output_dir("tasks_logs")
        initial = self.path_var.get().strip() or str(default_dir / "tasks_log.txt")
        selected = filedialog.asksaveasfilename(
            title=T("Select file path"),
            initialfile=Path(initial).name or "tasks_log.txt",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=str(Path(initial).parent if Path(initial).parent.exists() else default_dir),
        )
        if selected:
            self.path_var.set(selected)

    def build_report_text(self):
        plan = self.plan
        if plan is None and self.master is not None and hasattr(self.master, "plan"):
            plan = self.master.plan

        client_name = ""
        if self.master is not None and hasattr(self.master, "client_name_var"):
            client_name = str(self.master.client_name_var.get() or "").strip()
        if plan is not None:
            plan_client_name = str(getattr(plan, "client_name", "") or client_name or "").strip()
            if not plan_client_name and getattr(plan, "client", None) is not None:
                plan_client_name = str(getattr(plan.client, "name", "") or "").strip()
            return build_task_log_report_text(plan, client_name=plan_client_name)
        return build_task_log_report_text(client_name=client_name)

    def preview_report(self):
        ClientLogPreviewWindow(self, self.build_report_text())

    def save_report(self):
        target_path = self.path_var.get().strip()
        if not target_path:
            messagebox.showwarning(T("Select file path"), T("Select file path"))
            return

        destination = Path(target_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        report = append_report_footer(self.build_report_text().splitlines())
        destination.write_text("\n".join(report) + "\n", encoding="utf-8")
        messagebox.showinfo(T("Save Log"), f"Saved: {destination}")
        self.destroy()


class ExportReviewLogWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title(T("Export Review Log"))
        self.geometry("560x180")
        self.minsize(420, 150)

        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        default_dir = resolve_log_output_dir("observation_logs")
        default_path = default_dir / "review_log.txt"

        ttk.Label(main, text=T("Select file path")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        self.path_var = tk.StringVar(value=str(default_path))
        self.path_entry = ttk.Entry(main, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Button(main, text=T("Browse"), command=self.choose_file_path).grid(row=0, column=2, sticky="ew", padx=(8, 0), pady=(0, 8))

        action_row = ttk.Frame(main)
        action_row.grid(row=1, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(action_row, text=T("Preview"), command=self.preview_report).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text=T("Save Log"), command=self.save_report).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text=T("Home"), command=self.go_home).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text=T("Cancel"), command=self.destroy).pack(side="left")

    def go_home(self):
        self.destroy()
        open_welcome_home()

    def choose_file_path(self):
        default_dir = resolve_log_output_dir("observation_logs")
        initial = self.path_var.get().strip() or str(default_dir / "review_log.txt")
        selected = filedialog.asksaveasfilename(
            title=T("Select file path"),
            initialfile=Path(initial).name or "review_log.txt",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=str(Path(initial).parent if Path(initial).parent.exists() else default_dir),
        )
        if selected:
            self.path_var.set(selected)

    def build_report_text(self):
        client_name = ""
        review_text = ""
        if self.master is not None:
            if hasattr(self.master, "client_name_var"):
                client_name = str(self.master.client_name_var.get() or "").strip()
            if hasattr(self.master, "review_text"):
                review_text = str(self.master.review_text.get("1.0", "end") or "").strip()
        return build_review_log_report_text(client_name=client_name, review_text=review_text)

    def preview_report(self):
        ClientLogPreviewWindow(self, self.build_report_text())

    def save_report(self):
        target_path = self.path_var.get().strip()
        if not target_path:
            messagebox.showwarning(T("Select file path"), T("Select file path"))
            return

        destination = Path(target_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        report = append_report_footer(self.build_report_text().splitlines())
        destination.write_text("\n".join(report) + "\n", encoding="utf-8")
        messagebox.showinfo(T("Save Log"), f"Saved: {destination}")
        self.destroy()


class ClientReviewsLogWindow(tk.Toplevel):
    def __init__(self, master=None, manager=None):
        super().__init__(master)
        self.title(T("Client Reviews Log"))
        self.geometry("1100x560")
        self.minsize(900, 420)

        self.manager = manager or ClientManager("clients.json")
        self.manager.load_clients()

        self.tree = ttk.Treeview(
            self,
            columns=("client", "business", "date", "review", "comment"),
            show="headings",
            height=16,
        )
        self.tree.heading("client", text=T("Client"))
        self.tree.heading("business", text=T("Business"))
        self.tree.heading("date", text=T("Date"))
        self.tree.heading("review", text=T("Review"))
        self.tree.heading("comment", text=T("Comment"))
        self.tree.column("client", width=150, anchor="w")
        self.tree.column("business", width=170, anchor="w")
        self.tree.column("date", width=150, anchor="center")
        self.tree.column("review", width=300, anchor="w")
        self.tree.column("comment", width=280, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(12, 8))
        self.tree.bind("<<TreeviewSelect>>", self.on_review_selected)

        comment_frame = ttk.Frame(self)
        comment_frame.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Label(comment_frame, text=T("Comment")).pack(anchor="w")
        self.comment_text = tk.Text(comment_frame, height=3, wrap="word", font=("Segoe UI", 10))
        self.comment_text.pack(fill="x", pady=(4, 8))
        self.comment_text.configure(state="disabled")

        self.save_button = ttk.Button(comment_frame, text=T("Save Comment"), command=self.save_selected_comment)
        self.save_button.pack(anchor="e", pady=(0, 8))
        self.save_button.configure(state="disabled")

        self.refresh_view()

        button_row = ttk.Frame(self)
        button_row.pack(pady=(0, 12))
        ttk.Button(button_row, text=T("Print"), command=self.print_report).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Home"), command=self.go_home).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Close"), command=self.destroy).pack(side="left")

    def go_home(self):
        self.destroy()
        open_welcome_home()

    def print_report(self):
        reviews = self.manager.get_all_reviews()
        title = T("Client Reviews Log")
        lines = [title, ""]
        if not reviews:
            lines.append(T("No reviews yet"))
        else:
            for index, review in enumerate(reviews, start=1):
                lines.append(f"{index}. {review.get('client_name', '')} | {review.get('business', '')} | {review.get('date', '')}")
                lines.append(f"   {review.get('review', '')}")
                comment = str(review.get('comment', '')).strip()
                if comment:
                    lines.append(f"   Comment: {comment}")
                lines.append("")
        print_report_document(title, lines)

    def set_comment_entry_state(self, enabled: bool):
        if enabled:
            self.comment_text.configure(state="normal")
            self.save_button.configure(state="normal")
            return

        self.comment_text.configure(state="disabled")
        self.comment_text.delete("1.0", tk.END)
        self.save_button.configure(state="disabled")

    def on_review_selected(self, event=None):
        selected = self.tree.selection()
        if not selected:
            self.set_comment_entry_state(False)
            return

        values = self.tree.item(selected[0], "values")
        if len(values) >= 5:
            self.set_comment_entry_state(True)
            self.comment_text.delete("1.0", tk.END)
            self.comment_text.insert("1.0", values[4])
            return

        self.set_comment_entry_state(False)

    def save_selected_comment(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(T("No review selected"), T("Please select a review from the review log first."))
            return

        values = self.tree.item(selected[0], "values")
        if len(values) < 5:
            messagebox.showwarning(T("No review selected"), T("Please select a valid review from the review log."))
            return

        client_name = values[0]
        review_text = strip_task_number_prefix(values[3])
        comment_text = self.comment_text.get("1.0", tk.END).strip()

        if not client_name or not review_text:
            messagebox.showwarning(T("No review selected"), T("Select a valid review row first."))
            return

        updated = self.manager.update_review_comment(client_name, review_text, comment_text)
        if not updated:
            messagebox.showwarning(T("Comment not saved"), T("The selected review could not be updated."))
            return

        self.refresh_view()
        messagebox.showinfo(T("Comment saved"), T("Comment saved successfully."))

    def refresh_view(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        reviews = self.manager.get_all_reviews()
        if not reviews:
            self.tree.insert("", tk.END, values=(T("No reviews yet"), "", "", "", ""))
            self.set_comment_entry_state(False)
            return

        for index, review in enumerate(reviews, start=1):
            review_text = str(review.get("review", "")).strip()
            listed_review = f"{index}. {review_text}" if review_text else f"{index}."
            comment_text = str(review.get("comment", "")).strip()
            self.tree.insert(
                "",
                tk.END,
                values=(
                    review.get("client_name", ""),
                    review.get("business", ""),
                    review.get("date", ""),
                    listed_review,
                    comment_text,
                ),
            )

        self.set_comment_entry_state(False)


class ProgressApp(tk.Tk):
    @staticmethod
    def resolve_client_file():
        project_root = Path(__file__).resolve().parent.parent
        return resolve_clients_data_path(project_root=project_root)

    def __init__(self):
        super().__init__()
        global _ACTIVE_PROGRESS_APP
        _ACTIVE_PROGRESS_APP = self
        self.read_only_mode = is_guest_profile(CURRENT_SESSION_PROFILE)
        self.title(T("Client Progress Manager"))

        if APP_ICON.exists():
            try:
                self.iconbitmap(str(APP_ICON))
            except tk.TclError:
                pass

        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.geometry(f"{max(920, self.screen_width - 180)}x{max(620, self.screen_height - 180)}")
        self.minsize(900, 560)

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.option_add("*Font", "{Segoe UI} 8")
        self.style.configure(".", font=("Segoe UI", 8))

        self.client_file = self.resolve_client_file()
        if not self.client_file.exists():
            self.client_file.parent.mkdir(parents=True, exist_ok=True)
            self.client_file.write_text("[]", encoding="utf-8")
        self.client_manager = ClientManager(self.client_file)
        Plan.Clients_progress = {}
        for client in self.client_manager.clients:
            if isinstance(getattr(client, "progress", None), dict) and client.progress:
                Plan.Clients_progress[client.name] = dict(client.progress)

        self.client_name_var = tk.StringVar(value="")
        self.country_name_var = tk.StringVar(value=DEFAULT_COUNTRY)
        self.contact_var = tk.StringVar(value="")
        self.business_var = tk.StringVar(value="")
        self.shop_number_var = tk.StringVar(value="")
        self.address_var = tk.StringVar(value="")
        self.electrical_meter_var = tk.StringVar(value="")
        self.email_var = tk.StringVar(value="")
        self.review_var = tk.StringVar(value="")
        self.selected_shops = []
        self.total_tasks_var = tk.StringVar(value="0")
        self.new_task_var = tk.StringVar()

        self.plan = None
        self.client_combo = None
        self.protocol("WM_DELETE_WINDOW", self.close_overview_window)

        self.build_ui()

    def close_overview_window(self):
        global _ACTIVE_PROGRESS_APP, _ACTIVE_WELCOME_WINDOW
        if _ACTIVE_PROGRESS_APP is self:
            _ACTIVE_PROGRESS_APP = None
        self.destroy()
        if _ACTIVE_WELCOME_WINDOW is None:
            try:
                welcome = open_welcome_home()
                welcome.focus_set()
            except Exception:
                pass

    def build_ui(self):
        self.style.configure("Section.TLabelframe", padding=(10, 8), relief="groove")
        self.style.configure("Section.TLabelframe.Label", font=("Segoe UI", 8, "bold"))
        self.style.configure("Header.TLabel", font=("Segoe UI", 8, "bold"))
        self.style.configure(
            "Action.TButton",
            padding=(10, 6),
            font=("Segoe UI", 9, "bold"),
            foreground="#111827",
            background="#dbeafe",
            borderwidth=2,
            relief="raised",
        )
        self.style.map(
            "Action.TButton",
            background=[("active", "#93c5fd"), ("pressed", "#60a5fa")],
            foreground=[("active", "#111827"), ("pressed", "#ffffff")],
            relief=[("pressed", "sunken"), ("active", "raised")],
        )
        self.style.configure("Red.Horizontal.TProgressbar", background="#d32f2f", troughcolor="#e0e0e0")
        self.style.configure("Yellow.Horizontal.TProgressbar", background="#f9a825", troughcolor="#e0e0e0")
        self.style.configure("Green.Horizontal.TProgressbar", background="#2e7d32", troughcolor="#e0e0e0")

        self.translatable_labels = []
        self.translatable_buttons = []

        main = ttk.Frame(self, padding=14)
        main.pack(fill="both", expand=True)

        main.columnconfigure(0, weight=25)
        main.columnconfigure(1, weight=25)
        main.columnconfigure(2, weight=20)
        main.columnconfigure(3, weight=30)
        main.rowconfigure(1, weight=1)
        main.rowconfigure(2, weight=0)
        main.rowconfigure(3, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=0)
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=0)

        try:
            if Image is not None and ImageTk is not None and APP_ICON.exists():
                logo_image = Image.open(APP_ICON)
                if logo_image.size[0] > 0 and logo_image.size[1] > 0:
                    logo_image = logo_image.resize((32, 32), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
                    self.header_logo_image = ImageTk.PhotoImage(logo_image)
                    logo_label = tk.Label(header, image=self.header_logo_image, bd=0, highlightthickness=0)
                    logo_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
                else:
                    raise ValueError("empty icon size")
            else:
                raise ValueError("Pillow not available or icon missing")
        except Exception:
            self.header_logo_image = None
            logo_label = tk.Label(header, text="★", font=("Segoe UI", 18, "bold"), fg="#1f2937", bd=0)
            logo_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        title = tk.Label(
            header,
            text=T("Client Progress Manager"),
            font=("Segoe UI", 14, "bold"),
            fg="#1f2937",
            anchor="center",
        )
        self.translatable_labels.append((title, "Client Progress Manager"))
        title.grid(row=0, column=1, sticky="ew")

        lang_frame = ttk.Frame(header)
        lang_frame.grid(row=0, column=2, sticky="e", padx=(10, 0))
        lang_label = ttk.Label(lang_frame, text=T("Language"))
        lang_label.pack(side="left", padx=(0, 6))
        self.translatable_labels.append((lang_label, "Language"))
        self.language_var = tk.StringVar(value=CURRENT_LANGUAGE)
        self.language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.language_var,
            state="readonly",
            width=12,
            values=["eng", "ar"],
        )
        self.language_combo.pack(side="left")
        self.language_combo.bind("<<ComboboxSelected>>", self.switch_language)

        header_actions = ttk.Frame(header)
        header_actions.grid(row=0, column=3, sticky="e", padx=(10, 0))
        send_email_button = ttk.Button(header_actions, text=T("Send Email"), command=self.send_email_to_client, style="Action.TButton", width=14)
        send_email_button.pack(side="left", padx=(0, 6))
        self.translatable_buttons.append((send_email_button, "Send Email"))
        save_exit_button = ttk.Button(header_actions, text=T("Save & Exit"), command=self.save_and_exit, style="Action.TButton", width=14)
        save_exit_button.pack(side="left", padx=(0, 6))
        self.translatable_buttons.append((save_exit_button, "Save & Exit"))
        share_client_button = ttk.Button(header_actions, text=T("Share Client Info"), command=self.open_client_window, style="Action.TButton", width=16)
        share_client_button.pack(side="left")
        self.translatable_buttons.append((share_client_button, "Share Client Info"))
        home_button = ttk.Button(header_actions, text=T("Home"), command=self.go_home, style="Action.TButton", width=10)
        home_button.pack(side="left", padx=(6, 0))
        self.translatable_buttons.append((home_button, "Home"))
        logout_button = ttk.Button(header_actions, text=T("Logout"), command=self.logout_from_overview, style="Action.TButton", width=12)
        logout_button.pack(side="left", padx=(6, 0))
        self.translatable_buttons.append((logout_button, "Logout"))
        cancel_button = ttk.Button(header_actions, text=T("Cancel"), command=self.cancel_and_exit, style="Action.TButton", width=12)
        cancel_button.pack(side="left", padx=(6, 0))
        self.translatable_buttons.append((cancel_button, "Cancel"))

        self.details_frame = ttk.LabelFrame(main, text=T("Client Details"), style="Section.TLabelframe")
        self.translatable_labels.append((self.details_frame, "Client Details"))
        self.details_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(0, 6), pady=(0, 8))
        details_frame = self.details_frame
        details_frame.columnconfigure(1, weight=1)

        client_name_label = ttk.Label(details_frame, text=f"👤 {T('Client Name')}")
        set_emoji_translated_label(client_name_label, "Client Name", "👤 ")
        client_name_label.grid(row=0, column=0, sticky="w", padx=(10, 12), pady=(8, 6))
        self.translatable_labels.append((client_name_label, "Client Name"))
        self.client_combo = ttk.Combobox(details_frame, textvariable=self.client_name_var, state="normal")
        self.client_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(8, 6))
        self.client_combo.bind("<<ComboboxSelected>>", self.on_client_name_selected)
        self.refresh_client_combo()

        country_label = ttk.Label(details_frame, text=f"🌍 {T('Country')}")
        set_emoji_translated_label(country_label, "Country", "🌍 ")
        country_label.grid(row=1, column=0, sticky="w", padx=(10, 12), pady=(0, 6))
        self.translatable_labels.append((country_label, "Country"))
        self.country_combo = ttk.Combobox(details_frame, textvariable=self.country_name_var, values=COUNTRY_OPTIONS, state="readonly")
        self.country_combo.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 6))
        self.country_combo.current(COUNTRY_OPTIONS.index(DEFAULT_COUNTRY) if DEFAULT_COUNTRY in COUNTRY_OPTIONS else 0)

        contact_label = ttk.Label(details_frame, text=f"📞 {T('Contact')}")
        set_emoji_translated_label(contact_label, "Contact", "📞 ")
        contact_label.grid(row=2, column=0, sticky="w", padx=(10, 12), pady=(0, 6))
        self.translatable_labels.append((contact_label, "Contact"))
        self.contact_entry = ttk.Entry(
            details_frame,
            textvariable=self.contact_var,
            validate="key",
            validatecommand=(self.register(validate_contact_number), "%P"),
        )
        self.contact_entry.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=(0, 6))

        email_label = ttk.Label(details_frame, text=f"✉️ {T('Email')}")
        set_emoji_translated_label(email_label, "Email", "✉️ ")
        email_label.grid(row=3, column=0, sticky="w", padx=(10, 12), pady=(0, 6))
        self.translatable_labels.append((email_label, "Email"))
        self.email_entry = ttk.Entry(details_frame, textvariable=self.email_var)
        self.email_entry.grid(row=3, column=1, sticky="ew", padx=(0, 10), pady=(0, 6))

        business_label = ttk.Label(details_frame, text=f"🏢 {T('Business')}")
        set_emoji_translated_label(business_label, "Business", "🏢 ")
        business_label.grid(row=4, column=0, sticky="w", padx=(10, 12), pady=(0, 6))
        self.translatable_labels.append((business_label, "Business"))
        self.business_entry = ttk.Entry(details_frame, textvariable=self.business_var)
        self.business_entry.grid(row=4, column=1, sticky="ew", padx=(0, 10), pady=(0, 6))

        shop_label = ttk.Label(details_frame, text=f"🏪 {T('Shop Number')}")
        set_emoji_translated_label(shop_label, "Shop Number", "🏪 ")
        shop_label.grid(row=5, column=0, sticky="w", padx=(10, 12), pady=(0, 8))
        self.translatable_labels.append((shop_label, "Shop Number"))
        self.shop_number_entry = ttk.Entry(details_frame, textvariable=self.shop_number_var)
        self.shop_number_entry.grid(row=5, column=1, sticky="ew", padx=(0, 10), pady=(0, 8))
        self.shop_number_entry.bind("<FocusOut>", self._sync_electrical_meter_from_shop_number)
        self.shop_number_entry.bind("<Return>", self._sync_electrical_meter_from_shop_number)

        address_label = ttk.Label(details_frame, text=f"📍 {T('Address')}")
        set_emoji_translated_label(address_label, "Address", "📍 ")
        address_label.grid(row=6, column=0, sticky="w", padx=(10, 12), pady=(0, 6))
        self.translatable_labels.append((address_label, "Address"))
        self.address_entry = ttk.Entry(details_frame, textvariable=self.address_var)
        self.address_entry.grid(row=6, column=1, sticky="ew", padx=(0, 10), pady=(0, 6))

        electrical_meter_label = ttk.Label(details_frame, text=f"⚡ {T('Electrical Meter')}")
        set_emoji_translated_label(electrical_meter_label, "Electrical Meter", "⚡ ")
        electrical_meter_label.grid(row=7, column=0, sticky="w", padx=(10, 12), pady=(0, 8))
        self.translatable_labels.append((electrical_meter_label, "Electrical Meter"))
        self.electrical_meter_entry = ttk.Entry(details_frame, textvariable=self.electrical_meter_var)
        self.electrical_meter_entry.grid(row=7, column=1, sticky="ew", padx=(0, 10), pady=(0, 8))

        self.review_frame = ttk.LabelFrame(main, text=T("Client Review"), style="Section.TLabelframe")
        self.translatable_labels.append((self.review_frame, "Client Review"))
        self.review_frame.grid(row=1, column=2, columnspan=2, sticky="nsew", padx=(6, 0), pady=(0, 8))
        self.review_frame.columnconfigure(0, weight=1)
        review_frame = self.review_frame

        review_frame.columnconfigure(0, weight=0)
        review_frame.columnconfigure(1, weight=1)

        client_actions_frame = tk.Frame(review_frame, bg="#edf6ff", bd=1, highlightthickness=1, highlightbackground="#c9d8ea")
        client_actions_frame.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(10, 6), pady=(8, 8))
        client_actions_frame.grid_columnconfigure(0, weight=1)

        self.read_only_action_buttons = []
        client_action_specs = [
            (T("Add Client"), self.add_new_client, 18),
            (T("Save Client"), self.save_current_client, 18),
            (T("All Clients"), self.open_all_clients, 18),
            (T("Reservation Status"), self.open_reservation_status_window, 20),
            (T("Export Clients Log"), self.export_client_log, None),
        ]

        for idx, (text, command, width) in enumerate(client_action_specs):
            button = ttk.Button(
                client_actions_frame,
                text=text,
                command=command,
                style="Action.TButton",
                width=width if width is not None else 20,
            )
            button.grid(row=idx, column=0, sticky="ew", padx=(8, 8), pady=(6, 0))
            self.translatable_buttons.append((button, text))
            self.read_only_action_buttons.append(button)

        self.review_text = tk.Text(review_frame, width=30, height=4, wrap="word", font=("Segoe UI", 9))
        self.review_text.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=(8, 6))

        review_buttons = ttk.Frame(review_frame)
        review_buttons.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=(0, 8))
        for col_index in range(2):
            review_buttons.columnconfigure(col_index, weight=1)

        review_action_specs = [
            (T("Add Review"), self.add_client_review, None),
            (T("Save Review"), self.save_client_review, None),
            (T("Export Review Log"), self.export_observation_log, None),
            (T("Open Review Log"), self.open_reviews_log, None),
        ]

        for idx, (text, command, width) in enumerate(review_action_specs):
            row = idx // 2
            col = idx % 2
            button = ttk.Button(
                review_buttons,
                text=text,
                command=command,
                style="Action.TButton",
                width=width if width is not None else 20,
            )
            button.grid(row=row, column=col, sticky="ew", padx=(0, 8), pady=(0, 6))
            self.translatable_buttons.append((button, text))
            self.read_only_action_buttons.append(button)

        self.progress_box = ttk.LabelFrame(main, text=T("Progress Overview"), style="Section.TLabelframe")
        self.translatable_labels.append((self.progress_box, "Progress Overview"))
        self.progress_box.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(0, 4))
        self.progress_box.columnconfigure(1, weight=1)
        progress_box = self.progress_box

        progress_label = ttk.Label(progress_box, text=T("Progress"))
        progress_label.grid(row=0, column=0, sticky="w", padx=(10, 12), pady=(6, 2))
        self.translatable_labels.append((progress_label, "Progress"))
        self.progress_var = tk.StringVar(value="0%")
        progress_value_label = ttk.Label(progress_box, textvariable=self.progress_var, font=("Segoe UI", 10, "bold"))
        progress_value_label.grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(6, 2))

        self.progress_bar = ttk.Progressbar(progress_box, orient="horizontal", length=440, mode="determinate")
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(10, 10), pady=(0, 6))
        self._apply_progress_bar_color(0)

        total_tasks_label = ttk.Label(progress_box, text=T("Total Tasks"))
        total_tasks_label.grid(row=2, column=0, sticky="w", padx=(10, 12), pady=(0, 4))
        self.translatable_labels.append((total_tasks_label, "Total Tasks"))
        self.total_entry = ttk.Entry(progress_box, textvariable=self.total_tasks_var, state="readonly")
        self.total_entry.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=(0, 4))

        self.tasks_frame = ttk.LabelFrame(main, text=T("Tasks"), style="Section.TLabelframe")
        self.translatable_labels.append((self.tasks_frame, "Tasks"))
        self.tasks_frame.grid(row=4, column=0, columnspan=4, sticky="nsew", pady=(0, 6))
        self.tasks_frame.columnconfigure(0, weight=2)
        self.tasks_frame.columnconfigure(1, weight=0)
        self.tasks_frame.columnconfigure(2, weight=2)
        self.tasks_frame.columnconfigure(3, weight=0)
        self.tasks_frame.columnconfigure(4, weight=1, minsize=170)
        self.tasks_frame.rowconfigure(1, weight=1)
        tasks_frame = self.tasks_frame

        all_tasks_label = ttk.Label(tasks_frame, text=T("All Tasks"), font=("Segoe UI", 10, "bold"))
        all_tasks_label.grid(row=0, column=0, sticky="n", padx=(10, 0), pady=(0, 2))
        self.translatable_labels.append((all_tasks_label, "All Tasks"))
        pending_tasks_label = ttk.Label(tasks_frame, text=T("Pending Tasks"), font=("Segoe UI", 10, "bold"))
        pending_tasks_label.grid(row=0, column=2, sticky="n", padx=(10, 0), pady=(0, 2))
        self.translatable_labels.append((pending_tasks_label, "Pending Tasks"))

        list_area = ttk.Frame(tasks_frame)
        list_area.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=(8, 0), pady=(0, 0))
        list_area.columnconfigure(0, weight=2)
        list_area.columnconfigure(1, weight=0)
        list_area.columnconfigure(2, weight=2)
        list_area.columnconfigure(3, weight=0)

        all_scroll = ttk.Scrollbar(list_area, orient="vertical")
        pending_scroll = ttk.Scrollbar(list_area, orient="vertical")
        all_h_scroll = ttk.Scrollbar(list_area, orient="horizontal")
        pending_h_scroll = ttk.Scrollbar(list_area, orient="horizontal")

        self.all_tasks_box = tk.Listbox(
            list_area,
            height=8,
            width=28,
            exportselection=False,
            bg="#ffffff",
            selectmode="browse",
            font=("Segoe UI", 10),
            yscrollcommand=all_scroll.set,
            xscrollcommand=all_h_scroll.set,
            relief="solid",
            borderwidth=1,
        )
        self.pending_tasks_box = tk.Listbox(
            list_area,
            height=8,
            width=28,
            exportselection=False,
            bg="#fffef5",
            selectmode="browse",
            font=("Segoe UI", 10),
            yscrollcommand=pending_scroll.set,
            xscrollcommand=pending_h_scroll.set,
            relief="solid",
            borderwidth=1,
        )

        all_scroll.config(command=self.all_tasks_box.yview)
        pending_scroll.config(command=self.pending_tasks_box.yview)
        all_h_scroll.config(command=self.all_tasks_box.xview)
        pending_h_scroll.config(command=self.pending_tasks_box.xview)

        self.all_tasks_box.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 0))
        all_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=(0, 0))
        all_h_scroll.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 6), pady=(0, 0))
        self.pending_tasks_box.grid(row=0, column=2, sticky="nsew", padx=(0, 4), pady=(0, 0))
        pending_scroll.grid(row=0, column=3, sticky="ns", padx=(0, 0), pady=(0, 0))
        pending_h_scroll.grid(row=1, column=2, columnspan=2, sticky="ew", padx=(0, 0), pady=(0, 0))

        button_row = ttk.Frame(tasks_frame)
        button_row.grid(row=1, column=4, sticky="nse", padx=(6, 8), pady=(0, 6))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)

        action_buttons = [
            (T("Tasks Details"), self.open_task_details_window),
            (T("Contract Details"), self.open_contract_details_window),
            (T("Transactions"), self.open_transactions_window),
            (T("Payment Report"), self.open_payment_report_window),
            (T("Refresh Progress"), self.refresh_display),
            (T("Export Task Log"), self.export_task_log),
        ]

        for idx, (text, command) in enumerate(action_buttons):
            column = idx % 2
            row = idx // 2
            button = ttk.Button(
                button_row,
                text=text,
                command=command,
                style="Action.TButton",
            )
            button.grid(row=row, column=column, sticky="ew", padx=(0, 4), pady=(0, 4))
            button.configure(width=max(18, len(text) + 4))
            self.translatable_buttons.append((button, text))
            self.read_only_action_buttons.append(button)

        main.rowconfigure(4, weight=2)
        tasks_frame.rowconfigure(1, weight=1)

        self.clear_client_form()
        self.apply_access_mode()

    def _guest_allowed_button_texts(self):
        return {
            T("All Clients"),
            T("Tasks Details"),
            T("Export Clients Log"),
            T("Export Task Log"),
            T("Export Review Log"),
            T("Open Review Log"),
        }

    def apply_access_mode(self):
        self.read_only_mode = is_guest_profile(CURRENT_SESSION_PROFILE)
        read_only = self.read_only_mode
        guest_allowed = self._guest_allowed_button_texts()

        for widget in (
            self.client_combo,
            self.country_combo,
            self.contact_entry,
            self.email_entry,
            self.business_entry,
            self.shop_number_entry,
            self.address_entry,
            self.electrical_meter_entry,
        ):
            if widget is None or not widget.winfo_exists():
                continue
            widget.configure(state="readonly" if read_only and hasattr(widget, "configure") else "normal")

        if self.review_text is not None and self.review_text.winfo_exists():
            self.review_text.configure(state="disabled" if read_only else "normal")

        for button in getattr(self, "read_only_action_buttons", []):
            if button is None or not button.winfo_exists():
                continue
            button_label = button.cget("text")
            if read_only and button_label not in guest_allowed:
                button.configure(state="disabled")
            else:
                button.configure(state="normal")

        self.refresh_client_combo()

    def switch_language(self, event=None):
        selected = self.language_var.get()
        if selected not in {"eng", "ar"}:
            selected = "eng"
        set_language(selected)
        self.language_var.set(CURRENT_LANGUAGE)
        self.refresh_lang_ui()

    def refresh_lang_ui(self):
        for widget, original_text in getattr(self, "translatable_labels", []):
            try:
                emoji_prefix = getattr(widget, "_emoji_prefix", "")
                if emoji_prefix:
                    updated_text = f"{emoji_prefix}{T(original_text)}"
                    widget.configure(text=updated_text)
                    configure_emoji_label(widget, updated_text, size=10, bold=True)
                else:
                    widget.configure(text=T(original_text))
            except Exception:
                pass

        for widget, original_text in getattr(self, "translatable_buttons", []):
            try:
                widget.configure(text=T(original_text))
            except Exception:
                pass

        self.title(T("Client Progress Manager"))
        self.refresh_client_combo()
        if hasattr(self, "all_tasks_box"):
            self.refresh_display()

    def update_window_texts(self):
        if self.client_combo is not None:
            self.client_combo.set(self.client_name_var.get() or T("<New Client>"))
            self.refresh_client_combo()

        if hasattr(self, "all_tasks_box"):
            self.all_tasks_box.delete(0, tk.END)
            self.pending_tasks_box.delete(0, tk.END)
            if self.plan is None:
                self.all_tasks_box.insert(tk.END, T("No client selected"))
                self.pending_tasks_box.insert(tk.END, T("No pending tasks"))
            else:
                self.refresh_display()

    def refresh_client_combo(self):
        self.client_manager.load_clients()
        names = [client.name for client in self.client_manager.clients]
        new_client_label = T("<New Client>")
        combo_values = [new_client_label] + names
        self.client_combo.configure(values=combo_values)
        if self.client_name_var.get() in combo_values:
            self.client_combo.set(self.client_name_var.get())
        else:
            self.client_combo.set(new_client_label)

    def clear_client_form(self):
        self.plan = None
        self.selected_shops = []
        self.client_name_var.set("")
        self.country_name_var.set(DEFAULT_COUNTRY)
        self.contact_var.set("")
        self.business_var.set("")
        self.shop_number_var.set("")
        self.address_var.set("")
        self.electrical_meter_var.set("")
        self.email_var.set("")
        self.total_tasks_var.set("0")
        self.new_task_var.set("")
        self.progress_var.set("0%")
        self.progress_bar["value"] = 0
        self.progress_bar.configure(style="Red.Horizontal.TProgressbar")
        self.all_tasks_box.delete(0, tk.END)
        self.pending_tasks_box.delete(0, tk.END)
        self.all_tasks_box.insert(tk.END, T("No client selected"))
        self.pending_tasks_box.insert(tk.END, T("No pending tasks"))

    def go_home(self):
        self.destroy()
        open_welcome_home()

    def logout_from_overview(self):
        sync_session_profile(clear=True)
        self.close_overview_window()
        open_welcome_home()

    def focus_section(self, section_name):
        section_name = (section_name or "details").lower()
        targets = {
            "details": self.details_frame,
            "clients": self.details_frame,
            "review": self.review_frame,
            "reviews": self.review_frame,
            "tasks": self.tasks_frame,
            "progress": self.progress_box,
            "overview": self.progress_box,
        }
        target = targets.get(section_name, self.details_frame)
        if target is not None:
            self.update_idletasks()
            self.focus_set()
            try:
                target.focus_set()
            except Exception:
                pass
            try:
                target.tkraise()
            except Exception:
                pass

    def on_client_name_selected(self, event=None):
        name = self.client_name_var.get().strip()
        if not name:
            self.clear_client_form()
            return

        if name == T("<New Client>"):
            self.clear_client_form()
            self.client_name_var.set("")
            return

        self.client_manager.load_clients()
        matching_client = next(
            (client for client in self.client_manager.clients if client.name.lower() == name.lower()),
            None,
        )

        if matching_client is None:
            self.clear_client_form()
            self.client_name_var.set(name)
            return

        self.load_client_progress(matching_client.name, matching_client.business)
        local_number, country_name = parse_contact_for_ui(matching_client.contact)
        self.contact_var.set(local_number)
        self.country_name_var.set(country_name if country_name in COUNTRY_OPTIONS else DEFAULT_COUNTRY)
        self.business_var.set(matching_client.business)
        self.shop_number_var.set(str(matching_client.shop_number))
        self.address_var.set(getattr(matching_client, "address", ""))
        self.electrical_meter_var.set(str(getattr(matching_client, "electrical_meter", getattr(matching_client, "notes", ""))))
        self.email_var.set(matching_client.email)

    def _parse_task_list(self):
        task_text = self.new_task_var.get().strip()
        if task_text:
            return parse_task_items(task_text, fallback_total=0)

        try:
            total = int(self.total_tasks_var.get())
        except ValueError:
            total = 0

        if total <= 0:
            return []
        return [f"Task {i}" for i in range(1, total + 1)]

    def delete_selected_client(self):
        name = self.client_name_var.get().strip()
        if not name or name == T("<New Client>"):
            messagebox.showwarning(T("No client selected"), T("Select an existing client first."))
            return

        confirm = messagebox.askyesno(
            T("Delete client?"),
            T("Are you sure you want to delete '{client_name}' from the client list?", client_name=name),
        )
        if not confirm:
            return

        removed = self.client_manager.delete_client(name)
        if not removed:
            messagebox.showwarning(T("Client not found"), T("'{client_name}' was not found in the saved client list.", client_name=name))
            return

        Plan.Clients_progress.pop(name, None)
        self.refresh_client_combo()
        self.clear_client_form()
        messagebox.showinfo(T("Client deleted"), T("'{client_name}' was removed successfully.", client_name=name))

    def _require_registered_user_for_changes(self, action_label="This action"):
        if is_guest_profile(CURRENT_SESSION_PROFILE):
            messagebox.showwarning(T("Access Denied"), T("Guest users are in read-only mode. {action_label} is not allowed.", action_label=action_label))
            return True
        return False

    def create_plan(self):
        if self._require_registered_user_for_changes(T("Create client plan")):
            return
        name = self.client_name_var.get().strip()
        if not name:
            messagebox.showwarning(T("Missing client"), T("Please enter a client name."))
            return

        contact = self.contact_var.get().strip()
        country_name = self.country_name_var.get().strip() or DEFAULT_COUNTRY
        country_code = normalize_country_code(COUNTRY_CODE_BY_NAME.get(country_name, DEFAULT_COUNTRY_CODE))
        business = self.business_var.get().strip()
        if not contact:
            messagebox.showwarning(T("Missing contact"), T("Please enter the client contact number."))
            return
        if not business:
            messagebox.showwarning(T("Missing business"), T("Please enter the client business type."))
            return

        email = self.email_var.get().strip()
        tasks = self._parse_task_list()

        if not tasks:
            messagebox.showwarning(T("Missing tasks"), T("Enter at least one task or set a total task count greater than zero."))
            return

        self.client_manager.load_clients()
        existing = next((client for client in self.client_manager.clients if client.name.lower() == name.lower()), None)
        formatted_contact = format_contact_number(contact, country_code)
        duplicate_contact = next(
            (client for client in self.client_manager.clients if client.contact == formatted_contact and client.name.lower() != name.lower()),
            None,
        )

        if duplicate_contact is not None:
            messagebox.showwarning(T("Duplicate contact"), T("A client with this contact number already exists."))
            return

        if existing is None:
            client = Client(name, formatted_contact, business, email)
            self.client_manager.clients.append(client)
        else:
            existing.contact = formatted_contact
            existing.business = business
            existing.email = email or existing.email
            client = existing

        self.client_manager.save_clients()

        self.plan = Plan(client, all_tasks=list(tasks))
        self.plan.sync_task_lists(all_tasks=list(tasks), pending_tasks=list(tasks))
        self.total_tasks_var.set(str(len(self.plan.all_tasks)))
        self.new_task_var.set("")
        self.refresh_display()

    def open_task_details_window(self):
        if is_guest_profile(CURRENT_SESSION_PROFILE):
            if self.plan is None:
                messagebox.showwarning(T("No client plan"), T("Create a client plan first."))
                return
        elif self._require_registered_user_for_changes(T("Task details")):
            return
        if self.plan is None:
            messagebox.showwarning(T("No client plan"), T("Create a client plan first."))
            return

        TaskDetailsWindow(
            self,
            client_name=self.client_name_var.get().strip() or self.plan.client_name,
            plan=self.plan,
            all_tasks=list(self.plan.all_tasks),
            pending_tasks=list(self.plan.pending_tasks),
        )

    def open_contract_details_window(self):
        if not is_registered_user_profile() or is_guest_profile(CURRENT_SESSION_PROFILE):
            messagebox.showwarning(T("Access Denied"), T("Registered users only. Guest access is limited to clients, reviews, tasks and payment reports."))
            return
        ContractDetailsWindow(self)

    def open_transactions_window(self):
        if not is_registered_user_profile() or is_guest_profile(CURRENT_SESSION_PROFILE):
            messagebox.showwarning(T("Access Denied"), T("Registered users only. Guest access is limited to clients, reviews, tasks and payment reports."))
            return
        ClientTransactionsWindow(self, self.client_name_var.get().strip())

    def open_payment_report_window(self):
        if is_guest_profile(CURRENT_SESSION_PROFILE):
            messagebox.showwarning(T("Access Denied"), T("Guest users cannot open payment reports. Overview is read-only."))
            return
        ClientPaymentReportWindow(self, self.client_name_var.get().strip())

    def focus_client_name_field(self):
        if hasattr(self, "client_combo") and self.client_combo.winfo_exists():
            self.client_combo.focus_set()
            try:
                self.client_combo.icursor(len(self.client_combo.get()))
            except Exception:
                pass
            return True
        return False

    def add_task(self):
        if self._require_registered_user_for_changes(T("Add task")):
            return
        name = self.client_name_var.get().strip()
        if not name or name == T("<New Client>"):
            self.focus_client_name_field()
            messagebox.showwarning(T("Clients name missing"), T("Clients name missing"))
            return

        if self.plan is None:
            self.focus_client_name_field()
            messagebox.showwarning(T("No client plan"), T("Create a client plan first."))
            return

        self.open_task_details_window()

    def save_task(self):
        if self._require_registered_user_for_changes(T("Save task")):
            return
        name = self.client_name_var.get().strip()
        if not name or name == T("<New Client>"):
            self.focus_client_name_field()
            messagebox.showwarning(T("Clients name missing"), T("Clients name missing"))
            return

        if self.plan is None:
            self.focus_client_name_field()
            messagebox.showwarning(T("No client plan"), T("Create a client plan first."))
            return

        if not hasattr(self, "new_task_entry") or not hasattr(self, "new_task_var"):
            self.open_task_details_window()
            return

        task = self.new_task_var.get().strip()
        if not task:
            self.new_task_entry.focus_set()
            self.new_task_entry.icursor(len(self.new_task_entry.get()))
            return

        self.plan.add_pending_task(task)
        self.refresh_display()
        self.new_task_var.set("")
        self.new_task_entry.focus_set()
        self.new_task_entry.icursor(0)

    def complete_selected_task(self):
        if self._require_registered_user_for_changes(T("Complete task")):
            return
        if self.plan is None:
            return

        selected = self.pending_tasks_box.curselection()
        if not selected:
            messagebox.showwarning(T("No task selected"), T("Select a task from the pending list."))
            return

        task = strip_task_number_prefix(self.pending_tasks_box.get(selected[0]))
        self.plan.complete_task(task)
        self.refresh_display()

    def _apply_progress_bar_color(self, value):
        if value < 33:
            self.progress_bar.configure(style="Red.Horizontal.TProgressbar")
        elif value < 66:
            self.progress_bar.configure(style="Yellow.Horizontal.TProgressbar")
        else:
            self.progress_bar.configure(style="Green.Horizontal.TProgressbar")

    def _build_payment_follow_up_tasks(self):
        if self.plan is None:
            return []

        client_name = self.client_name_var.get().strip() or self.plan.client_name
        if not client_name:
            return []

        self.client_manager.load_clients()
        client = next((item for item in self.client_manager.clients if item.name.lower() == client_name.lower()), None)
        if client is None:
            return []

        contract_details = getattr(client, "contract_details", {}) or {}
        start_date = str(contract_details.get("starting_date") or "").strip()
        end_date = str(contract_details.get("ending_date") or "").strip()
        months = generate_contract_months(start_date, end_date)
        if not months:
            return []

        transactions_by_month = {}
        for entry in getattr(client, "transactions", []) or []:
            month = str(entry.get("month", "") or "").strip()
            if month:
                transactions_by_month[month] = entry

        follow_up_tasks = []
        for month in months:
            entry = transactions_by_month.get(month)
            status = str((entry or {}).get("status", "") or "").strip().lower()
            if entry is not None and status in {"paid", "completed", "complete", "success", "successful"}:
                continue
            follow_up_tasks.append(f"Follow up payment for {client.name} - {month}")

        return follow_up_tasks

    def refresh_display(self):
        self.all_tasks_box.delete(0, tk.END)
        self.pending_tasks_box.delete(0, tk.END)

        if self.plan is None:
            self.all_tasks_box.insert(tk.END, T("No client selected"))
            self.pending_tasks_box.insert(tk.END, T("No pending tasks"))
            return

        payment_tasks = self._build_payment_follow_up_tasks()
        base_all_tasks = [task for task in self.plan.all_tasks if not str(task).startswith("Follow up payment for ")]
        base_pending_tasks = [task for task in self.plan.pending_tasks if not str(task).startswith("Follow up payment for ")]

        for task in payment_tasks:
            if task not in base_all_tasks:
                base_all_tasks.append(task)
            if task not in base_pending_tasks:
                base_pending_tasks.append(task)

        self.plan.sync_task_lists(all_tasks=base_all_tasks, pending_tasks=base_pending_tasks)
        self.progress_var.set(f"{self.plan.progress}%")
        self.progress_bar["value"] = self.plan.progress
        self._apply_progress_bar_color(self.plan.progress)
        self.total_tasks_var.set(str(len(self.plan.all_tasks)))

        if self.plan.all_tasks:
            for index, task in enumerate(self.plan.all_tasks, start=1):
                self.all_tasks_box.insert(tk.END, format_task_entry(task, number=index))
        else:
            self.all_tasks_box.insert(tk.END, T("No tasks yet"))

        if self.plan.pending_tasks:
            for index, task in enumerate(self.plan.pending_tasks, start=1):
                self.pending_tasks_box.insert(tk.END, format_task_entry(task, number=index))
        else:
            self.pending_tasks_box.insert(tk.END, T("No pending tasks"))

    def load_client_progress(self, client_name, business="N/A"):
        self.client_manager.load_clients()
        matching_client = next(
            (client for client in self.client_manager.clients if client.name.lower() == client_name.lower()),
            None,
        )

        if matching_client is not None:
            client = matching_client
            business = matching_client.business
            local_number, country_name = parse_contact_for_ui(matching_client.contact)
            self.contact_var.set(local_number)
            self.country_name_var.set(country_name if country_name in COUNTRY_OPTIONS else DEFAULT_COUNTRY)
            self.business_var.set(matching_client.business)
            self.shop_number_var.set(str(matching_client.shop_number))
            self.address_var.set(getattr(matching_client, "address", ""))
            self.electrical_meter_var.set(str(getattr(matching_client, "electrical_meter", getattr(matching_client, "notes", ""))))
            self.email_var.set(matching_client.email)
        else:
            client = Client(client_name, "N/A", business, shop_number="")

        saved = Plan.Clients_progress.get(client_name, {})
        all_tasks = list(saved.get("all_tasks", []))

        if not all_tasks:
            default_total = self.total_tasks_var.get().strip()
            try:
                total = int(default_total) if default_total else 5
            except ValueError:
                total = 5
            all_tasks = [T("Task {i}", i=i) for i in range(1, total + 1)]

        pending_tasks = list(saved.get("pending_tasks", all_tasks))
        self.client_name_var.set(client_name)
        self.plan = Plan(client, all_tasks=all_tasks)
        self.plan.sync_task_lists(all_tasks=all_tasks, pending_tasks=pending_tasks)
        self.total_tasks_var.set(str(len(self.plan.all_tasks)))
        self.refresh_display()

    def add_new_client(self):
        if self._require_registered_user_for_changes(T("Add client")):
            return
        self.clear_client_form()
        self.client_name_var.set(T("<New Client>"))
        if self.client_combo is not None and self.client_combo.winfo_exists():
            self.client_combo.set(T("<New Client>"))
        self.focus_client_name_field()

    def _sync_electrical_meter_from_shop_number(self, event=None):
        shop_number = str(self.shop_number_var.get()).strip()
        if not shop_number:
            return

        try:
            from logic.shops_conversion_to_dic import shop_meter_map, validate_shop
        except ImportError:
            shop_meter_map = load_shop_electrical_meter_map()
            validate_shop = None

        if validate_shop is not None:
            valid, msg = validate_shop(shop_number, self.selected_shops)
            if not valid:
                messagebox.showerror(T("Error"), T(msg))
                self.shop_number_var.set("")
                return

        meter_value = shop_meter_map.get(shop_number, "")
        if not meter_value:
            meter_value = load_shop_electrical_meter_map().get(shop_number, "")

        if meter_value:
            self.electrical_meter_var.set(str(meter_value))

        if shop_number and not any(str(item.get("Shop", "")).strip() == shop_number for item in self.selected_shops):
            self.selected_shops.append({"Shop": shop_number, "Elec meter": str(meter_value or "")})

    def save_current_client(self):
        if self._require_registered_user_for_changes(T("Save client")):
            return
        self.client_manager.load_clients()
        name = self.client_name_var.get().strip()
        if not name or name == T("<New Client>"):
            messagebox.showwarning(T("Missing client"), T("Please enter a client name before saving."))
            return

        if self.plan is not None and self.plan.client.name.lower() == name.lower():
            self.plan.update_clients_progress()

        contact = self.contact_var.get().strip()
        country_name = self.country_name_var.get().strip() or DEFAULT_COUNTRY
        country_code = normalize_country_code(COUNTRY_CODE_BY_NAME.get(country_name, DEFAULT_COUNTRY_CODE))
        business = self.business_var.get().strip()
        if not contact:
            messagebox.showwarning(T("Missing contact"), T("Please enter the client contact number before saving."))
            return
        if not business:
            messagebox.showwarning(T("Missing business"), T("Please enter the client business type before saving."))
            return

        existing = next(
            (client for client in self.client_manager.clients if client.name.lower() == name.lower()),
            None,
        )

        shop_number = str(self.shop_number_var.get()).strip()
        self._sync_electrical_meter_from_shop_number()
        valid_shop_number, shop_error = self.client_manager.validate_shop_number(shop_number, exclude_name=name)
        if not valid_shop_number:
            messagebox.showwarning(T("Shop number invalid"), T(shop_error))
            return

        formatted_contact = format_contact_number(contact, country_code)
        duplicate_contact = next(
            (client for client in self.client_manager.clients if client.contact == formatted_contact and client.name.lower() != name.lower()),
            None,
        )

        if duplicate_contact is not None:
            messagebox.showwarning(T("Duplicate contact"), T("A client with this contact number already exists."))
            return

        address = self.address_var.get().strip()
        electrical_meter = self.electrical_meter_var.get().strip()

        if existing is None:
            client = Client(
                name,
                formatted_contact,
                business,
                self.email_var.get().strip(),
                shop_number=shop_number,
                address=address,
                notes=electrical_meter,
            )
            self.client_manager.clients.append(client)
            self.client_manager.create_client_directory(client)
        else:
            existing.contact = formatted_contact
            existing.business = business
            existing.shop_number = shop_number
            existing.address = address
            existing.notes = electrical_meter
            existing.email = self.email_var.get().strip() or existing.email
            client = existing

        self.client_manager.save_clients()
        self.refresh_client_combo()
        self.client_name_var.set(name)

        if self.plan is None:
            self.plan = Plan(client, all_tasks=[])
        self.plan.client = client
        self.plan.client_name = client.name
        self.plan.update_clients_progress()
        client.progress = dict(Plan.Clients_progress.get(client.name, {}))
        self.client_manager.save_clients()
        self.refresh_display()
        messagebox.showinfo(T("Client saved"), T("'{name}' was saved successfully.", name=name))

    def send_email_to_client(self):
        if not is_registered_user_profile():
            messagebox.showwarning(T("Access Denied"), T("Registered users only. Guest access is limited to clients, reviews, tasks and payment reports."))
            return

        email = self.email_var.get().strip()
        if not email:
            messagebox.showwarning(T("No email"), T("This client does not have an email saved yet."))
            return

        user_profile = load_user_profile()
        user_email = user_profile.get("email", "")
        user_name = user_profile.get("name") or "User"
        gmail_params = [
            f"to={quote(email)}",
        ]
        if user_email:
            gmail_params.append(f"cc={quote(user_email)}")
        gmail_params.append(f"su={quote(f'Client communication - {user_name}')}")
        gmail_url = "https://mail.google.com/mail/?view=cm&fs=1&" + "&".join(gmail_params)
        if webbrowser.open(gmail_url):
            return

        mailto_url = f"mailto:{quote(email)}"
        if user_email:
            mailto_url = f"mailto:{quote(email)}?cc={quote(user_email)}"
        webbrowser.open(mailto_url)

    def confirm_exit_app(self):
        dialog = tk.Toplevel(self)
        dialog.title(T("Exit app"))
        dialog.geometry("420x160")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        message = ttk.Label(
            dialog,
            text=T("You are exiting the app. Ensure all entered data is saved; otherwise proceed to exit."),
            wraplength=360,
            justify="center",
        )
        message.pack(padx=20, pady=(18, 12))

        actions = ttk.Frame(dialog)
        actions.pack(pady=(0, 18))

        def close_dialog():
            dialog.destroy()

        cancel_button = ttk.Button(actions, text=T("Cancel"), command=close_dialog)
        cancel_button.pack(side="left", padx=(0, 10))

        proceed_button = ttk.Button(actions, text=T("Proceed to exit"), command=lambda: (self.destroy(), dialog.destroy()))
        proceed_button.pack(side="left")

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)
        self.wait_window(dialog)

    def save_and_exit(self):
        name = self.client_name_var.get().strip()
        if not name or name == T("<New Client>"):
            self.destroy()
            return

        self.save_current_client()
        self.client_manager.load_clients()
        self.client_manager.save_clients()
        self.destroy()

    def cancel_and_exit(self):
        self.confirm_exit_app()

    def add_client_review(self):
        if self._require_registered_user_for_changes(T("Add review")):
            return
        name = self.client_name_var.get().strip()
        if not name or name == T("<New Client>"):
            self.focus_client_name_field()
            messagebox.showwarning(T("Clients name missing"), T("Please fill the client name field first."))
            return

        self.review_text.focus_set()
        self.review_text.mark_set("insert", "1.0")

    def save_client_review(self):
        if self._require_registered_user_for_changes(T("Save review")):
            return
        name = self.client_name_var.get().strip()
        if not name or name == T("<New Client>"):
            self.focus_client_name_field()
            messagebox.showwarning(T("No client selected"), T("Select client first."))
            return

        review = self.review_text.get("1.0", "end").strip()
        if not review:
            messagebox.showwarning(T("No review"), T("Please type a review before saving it."))
            self.review_text.focus_set()
            self.review_text.mark_set("insert", "1.0")
            return

        if not self.client_manager.add_review(name, review):
            messagebox.showwarning(T("Client not found"), T("'{client_name}' was not found in the saved client list.", client_name=name))
            return

        self.review_text.delete("1.0", tk.END)
        self.review_text.focus_set()
        self.review_text.mark_set("insert", "1.0")
        messagebox.showinfo(T("Review saved"), T("Review saved for '{name}'.", name=name))

    def open_reviews_log(self):
        self.client_manager.load_clients()
        ClientReviewsLogWindow(self, self.client_manager)

    def export_client_log(self):
        ExportClientsLogWindow(self, self.client_manager)

    def export_task_log(self):
        ExportTaskLogWindow(self)

    def export_review_log(self):
        ExportReviewLogWindow(self)

    def export_observation_log(self):
        self.export_review_log()

    def open_client_window(self, client_name=None):
        ClientDetailsWindow(self, client_name=client_name or self.client_name_var.get().strip(), master_manager=self.client_manager)

    def open_all_clients(self):
        AllClientsProgressWindow(self)

    def open_reservation_status_window(self):
        if not is_registered_user_profile() or is_guest_profile(CURRENT_SESSION_PROFILE):
            messagebox.showwarning(T("Access Denied"), T("Registered users only. Guest access is limited to clients, reviews, tasks and payment reports."))
            return

        client_name = str(self.client_name_var.get() or "").strip()
        if client_name in {"", T("<New Client>")}:
            client_name = ""

        try:
            from ui.reservation_contract import ShopReservationForm
        except ImportError:
            messagebox.showerror(T("Form unavailable"), T("The reservation contract form could not be loaded."))
            return

        client_obj = None
        if client_name:
            self.client_manager.load_clients()
            client_obj = next((entry for entry in self.client_manager.clients if entry.name.strip().lower() == client_name.lower()), None)

        client_data = {
            "name": client_name or "",
            "shops": [
                {"Shop": str(item.get("Shop", "")).strip(), "Elec meter": str(item.get("Elec meter", "")).strip()}
                for item in self.selected_shops
                if str(item.get("Shop", "")).strip()
            ],
        }
        form = ShopReservationForm(client_name=client_name or None, client_data=client_data, client_obj=client_obj)
        form.grab_set()
        form.wait_window()


class ClientDetailsWindow(tk.Toplevel):
    def __init__(self, master=None, client_name=None, master_manager=None):
        super().__init__(master)
        self.title(T("Client Details"))
        self.geometry("540x420")
        self.minsize(500, 360)
        self.master_app = master
        self.manager = master_manager or getattr(master, "client_manager", ClientManager("clients.json"))
        self.client_name = client_name.strip() if client_name else ""
        self.client = self._find_client(self.client_name)
        self.edit_mode = False

        main = ttk.Frame(self, padding=14)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        self.fields = {}
        labels = [
            (T("Client Name"), "name"),
            (T("Country"), "country"),
            (T("Contact"), "contact"),
            (T("Business"), "business"),
            (T("Email"), "email"),
            (T("Shop Number"), "shop_number"),
            (T("Address"), "address"),
            (T("Electrical Meter"), "electrical_meter"),
        ]

        for index, (label_text, key) in enumerate(labels):
            ttk.Label(main, text=label_text).grid(row=index, column=0, sticky="w", padx=(0, 10), pady=(4, 6))
            var = tk.StringVar(value="")
            entry = ttk.Entry(main, textvariable=var)
            entry.grid(row=index, column=1, sticky="ew", pady=(4, 6))
            entry.configure(state="disabled")
            self.fields[key] = {"var": var, "entry": entry}

        vcard_frame = ttk.LabelFrame(main, text=T("vCard (.vcf)"), style="Section.TLabelframe")
        vcard_frame.grid(row=9, column=0, columnspan=2, sticky="nsew", pady=(8, 8))
        vcard_frame.columnconfigure(0, weight=1)
        self.vcard_text = tk.Text(vcard_frame, height=8, wrap="word", font=("Segoe UI", 9), state="disabled")
        self.vcard_text.grid(row=0, column=0, sticky="nsew", padx=(8, 8), pady=(8, 8))

        footer = ttk.Frame(main)
        footer.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(0, 0))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)
        footer.columnconfigure(2, weight=1)
        footer.columnconfigure(3, weight=1)

        ttk.Button(footer, text=T("Copy vCard (.vcf)"), command=self.share_client).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(footer, text=T("Edit"), command=self.toggle_edit).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(footer, text=T("Save"), command=self.save_client).grid(row=0, column=2, sticky="ew", padx=(0, 6))
        ttk.Button(footer, text=T("Cancel"), command=self.cancel_without_saving).grid(row=0, column=3, sticky="ew")

        self.populate_client()

    def _find_client(self, client_name):
        if not client_name:
            return None
        self.manager.load_clients()
        return next((client for client in self.manager.clients if client.name.lower() == client_name.lower()), None)

    def _set_editable(self, editable):
        self.edit_mode = editable
        for info in self.fields.values():
            info["entry"].configure(state="normal" if editable else "disabled")

    def _sync_electrical_meter_from_shop_number(self, event=None):
        shop_number = str(self.fields["shop_number"]["var"].get() or "").strip()
        if not shop_number:
            return
        meter_value = load_shop_electrical_meter_map().get(shop_number)
        if meter_value:
            self.fields["electrical_meter"]["var"].set(meter_value)

    def toggle_edit(self):
        self._set_editable(not self.edit_mode)

    def populate_client(self):
        if self.client is None:
            self.fields["name"]["var"].set(self.client_name)
            self.fields["country"]["var"].set(DEFAULT_COUNTRY)
            self.fields["contact"]["var"].set("")
            self.fields["business"]["var"].set("")
            self.fields["email"]["var"].set("")
            self.fields["shop_number"]["var"].set("")
            self.fields["address"]["var"].set("")
            self.fields["electrical_meter"]["var"].set("")
            self._render_vcard_preview()
            return

        self.fields["name"]["var"].set(self.client.name)
        country_name = parse_contact_for_ui(self.client.contact)[1]
        self.fields["country"]["var"].set(country_name if country_name in COUNTRY_OPTIONS else DEFAULT_COUNTRY)
        self.fields["contact"]["var"].set(parse_contact_for_ui(self.client.contact)[0])
        self.fields["business"]["var"].set(self.client.business)
        self.fields["email"]["var"].set(self.client.email)
        self.fields["shop_number"]["var"].set(getattr(self.client, "shop_number", ""))
        self.fields["address"]["var"].set(getattr(self.client, "address", ""))
        self.fields["electrical_meter"]["var"].set(getattr(self.client, "electrical_meter", getattr(self.client, "notes", "")))
        self._render_vcard_preview()

    def _render_vcard_preview(self):
        try:
            client = self._build_client_from_form()
        except ValueError:
            client = self.client
        if client is None:
            preview = ""
        else:
            preview = client.to_vcard()

        self.vcard_text.configure(state="normal")
        self.vcard_text.delete("1.0", tk.END)
        self.vcard_text.insert("1.0", preview)
        self.vcard_text.configure(state="disabled")

    def _build_client_from_form(self):
        name = self.fields["name"]["var"].get().strip()
        contact = self.fields["contact"]["var"].get().strip()
        business = self.fields["business"]["var"].get().strip()
        email = self.fields["email"]["var"].get().strip()
        shop_number = self.fields["shop_number"]["var"].get().strip()
        address = self.fields["address"]["var"].get().strip()
        electrical_meter = self.fields["electrical_meter"]["var"].get().strip()
        country_name = self.fields["country"]["var"].get().strip() or DEFAULT_COUNTRY
        country_code = normalize_country_code(COUNTRY_CODE_BY_NAME.get(country_name, DEFAULT_COUNTRY_CODE))
        if not name:
            raise ValueError(T("Please enter a client name before saving."))
        if not contact:
            raise ValueError(T("Please enter the client contact number before saving."))
        if not business:
            raise ValueError(T("Please enter the client business type before saving."))
        valid, error = self.manager.validate_shop_number(shop_number, exclude_name=name)
        if not valid:
            raise ValueError(T(error))
        return Client(name, format_contact_number(contact, country_code), business, email, shop_number=shop_number, address=address, notes=electrical_meter)

    def share_client(self):
        try:
            client = self._build_client_from_form()
        except ValueError as exc:
            messagebox.showwarning(T("Missing information"), str(exc))
            return

        payload = client.to_vcard()
        try:
            self.clipboard_clear()
            self.clipboard_append(payload)
        except Exception:
            pass
        messagebox.showinfo(T("Copy vCard (.vcf)"), T("Client details copied to the clipboard."))

    def save_client(self):
        try:
            client = self._build_client_from_form()
        except ValueError as exc:
            messagebox.showwarning(T("Missing information"), str(exc))
            return

        self.manager.load_clients()
        existing = next((item for item in self.manager.clients if item.name.lower() == client.name.lower()), None)
        if existing is None:
            self.manager.clients.append(client)
            self.manager.create_client_directory(client)
        else:
            existing.name = client.name
            existing.contact = client.contact
            existing.business = client.business
            existing.email = client.email
            existing.shop_number = client.shop_number
            existing.address = client.address
            existing.notes = client.notes
            client = existing

        self.manager.save_clients()

        if self.master_app is not None:
            if hasattr(self.master_app, "refresh_client_combo"):
                self.master_app.refresh_client_combo()
            if hasattr(self.master_app, "client_name_var"):
                self.master_app.client_name_var.set(client.name)
            if hasattr(self.master_app, "load_client_progress"):
                self.master_app.load_client_progress(client.name, client.business)

        messagebox.showinfo(T("Client saved"), T("'{name}' was saved successfully.", name=client.name))
        self.destroy()

    def cancel_without_saving(self):
        self.destroy()


class ReservationStatusWindow(tk.Toplevel):
    @staticmethod
    def _normalize_status_value(value, *, kind):
        candidate = str(value or "").strip().lower()
        if kind == "deposit":
            if candidate in {"deposite recieved", "deposit received", "received", "تم استلام الإيداع", "تم استلام الدفعة"}:
                return "Deposite recieved"
            if candidate in {"deposite not recieved", "deposit not received", "not received", "لم يتم استلام الإيداع", "لم يتم استلام الدفعة"}:
                return "Deposite not recieved"
            return "Deposite not recieved"
        if candidate in {"completed", "complete", "done", "مكتمل", "تم"}:
            return "completed"
        if candidate in {"under progress", "in progress", "pending", "قيد التنفيذ", "قيد التقدم", "معلق"}:
            return "under progress"
        return "under progress"

    def _deposit_status_display_values(self):
        return [T("Deposit received"), T("Deposit not received")]

    def _contract_status_display_values(self, deposit_status):
        normalized = self._normalize_status_value(deposit_status, kind="deposit")
        if normalized == "Deposite recieved":
            return [T("Completed"), T("Under progress")]
        return [T("Under progress")]

    def __init__(self, master=None):
        super().__init__(master)
        self.title(T("Reservation Status"))
        self.geometry("500x360")
        self.minsize(420, 300)
        self.master_app = master
        self.manager = getattr(master, "client_manager", ClientManager("clients.json")) if master is not None else ClientManager("clients.json")

        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        self.client_name_var = tk.StringVar(value="")
        self.contact_var = tk.StringVar(value="")
        self.shop_number_var = tk.StringVar(value="")
        self.electrical_meter_var = tk.StringVar(value="")
        self.deposit_status_var = tk.StringVar(value=T("Deposit not received"))
        self.contract_status_var = tk.StringVar(value=T("Under progress"))

        if self.master_app is not None:
            if hasattr(self.master_app, "client_name_var"):
                current_name = str(self.master_app.client_name_var.get() or "").strip()
                if current_name and current_name != T("<New Client>"):
                    self.client_name_var.set(current_name)
            if hasattr(self.master_app, "contact_var"):
                self.contact_var.set(self.master_app.contact_var.get().strip())
            if hasattr(self.master_app, "shop_number_var"):
                self.shop_number_var.set(self.master_app.shop_number_var.get().strip())
            if hasattr(self.master_app, "electrical_meter_var"):
                self.electrical_meter_var.set(self.master_app.electrical_meter_var.get().strip())

        if self.shop_number_var.get():
            self.electrical_meter_var.set(resolve_shop_electrical_meter(self.shop_number_var.get()))

        if self.client_name_var.get():
            client = self._find_client(self.client_name_var.get())
            if client is not None:
                reservation = getattr(client, "reservation_status", {}) or {}
                if reservation.get("client_name"):
                    self.client_name_var.set(reservation.get("client_name", self.client_name_var.get()))
                if reservation.get("contact"):
                    self.contact_var.set(reservation.get("contact", self.contact_var.get()))
                if reservation.get("shop_number"):
                    self.shop_number_var.set(reservation.get("shop_number", self.shop_number_var.get()))
                if reservation.get("deposit_status"):
                    self.deposit_status_var.set(reservation.get("deposit_status", self.deposit_status_var.get()))
                if reservation.get("contract_status"):
                    self.contract_status_var.set(reservation.get("contract_status", self.contract_status_var.get()))

        fields = [
            (T("Client Name"), self.client_name_var),
            (T("Contact"), self.contact_var),
            (T("Shop Number to Reserve"), self.shop_number_var),
        ]

        for row_index, (label_text, var) in enumerate(fields):
            ttk.Label(main, text=label_text, font=("Segoe UI", 10, "bold")).grid(row=row_index, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
            ttk.Entry(main, textvariable=var, width=30).grid(row=row_index, column=1, sticky="ew", pady=(0, 8))

        self.shop_number_var.trace_add("write", self._sync_meter_from_shop_number)

        ttk.Label(main, text=T("Electrical Meter"), font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
        ttk.Entry(main, textvariable=self.electrical_meter_var, width=30).grid(row=3, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(main, text=T("Deposit Money Received"), font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
        deposit_combo = ttk.Combobox(
            main,
            textvariable=self.deposit_status_var,
            values=self._deposit_status_display_values(),
            state="readonly",
            width=28,
        )
        deposit_combo.grid(row=4, column=1, sticky="ew", pady=(0, 8))
        deposit_combo.bind("<<ComboboxSelected>>", self._update_contract_status_option)

        ttk.Label(main, text=T("Preliminary Contract Status"), font=("Segoe UI", 10, "bold")).grid(row=5, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
        status_values = self._contract_status_display_values(self.deposit_status_var.get())
        self.contract_status_var.set(status_values[0] if status_values else T("Under progress"))
        status_combo = ttk.Combobox(main, textvariable=self.contract_status_var, values=status_values, state="readonly", width=28)
        status_combo.grid(row=5, column=1, sticky="ew", pady=(0, 8))

        button_row = ttk.Frame(main)
        button_row.grid(row=6, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(button_row, text=T("Save"), command=self.save_status).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Close"), command=self.destroy).pack(side="left")

        self.bind("<Escape>", lambda event: self.destroy())

    def _sync_meter_from_shop_number(self, *args):
        shop_number = self.shop_number_var.get().strip()
        self.electrical_meter_var.set(resolve_shop_electrical_meter(shop_number))

    def _update_contract_status_option(self, event=None):
        deposit_value = self._normalize_status_value(self.deposit_status_var.get(), kind="deposit")
        if deposit_value == "Deposite recieved":
            self.contract_status_var.set(T("Completed"))
            options = [T("Completed"), T("Under progress")]
        else:
            self.contract_status_var.set(T("Under progress"))
            options = [T("Under progress")]

        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):
                for widget in child.winfo_children():
                    if isinstance(widget, ttk.Combobox) and widget["state"] == "readonly":
                        try:
                            widget.configure(values=options)
                        except Exception:
                            pass

    def _find_client(self, client_name):
        if not client_name:
            return None
        self.manager.load_clients()
        return next((client for client in self.manager.clients if client.name.lower() == client_name.lower()), None)

    def _available_shop_numbers(self, current_client_name=""):
        shop_file = Path(__file__).resolve().parent / "Shops_Elect_meters.json"
        known_shops = []
        if shop_file.exists():
            try:
                with shop_file.open("r", encoding="utf-8") as infile:
                    data = json.load(infile)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            shop = str(item.get("Shop") or item.get("shop") or "").strip()
                            if shop:
                                known_shops.append(shop)
            except (json.JSONDecodeError, OSError, TypeError):
                pass

        if not known_shops:
            known_shops = [str(index) for index in range(1, 101)]

        self.manager.load_clients()
        used_shops = set()
        for client in self.manager.clients:
            shop_value = str(getattr(client, "shop_number", "") or "").strip()
            if not shop_value:
                continue
            if current_client_name and client.name.strip().lower() == current_client_name.strip().lower():
                continue
            used_shops.add(shop_value)

        available = [shop for shop in known_shops if shop not in used_shops]
        return available

    def save_status(self):
        client_name = self.client_name_var.get().strip()
        contact = self.contact_var.get().strip()
        shop_number = self.shop_number_var.get().strip()
        deposit_status = self._normalize_status_value(self.deposit_status_var.get(), kind="deposit") or "Deposite not recieved"
        contract_status = self._normalize_status_value(self.contract_status_var.get(), kind="contract") or "under progress"
        electrical_meter = str(self.electrical_meter_var.get().strip() or resolve_shop_electrical_meter(shop_number) or "")

        if deposit_status.lower() == "deposite recieved":
            contract_status = "completed" if contract_status.lower() in {"completed", "complete", "done"} else "completed"
        else:
            contract_status = "under progress"

        if not client_name:
            messagebox.showwarning(T("Missing client"), T("Please enter the client name before saving the reservation status."))
            return
        if not contact:
            messagebox.showwarning(T("Missing contact"), T("Please enter the client contact number before saving the reservation status."))
            return
        if not shop_number:
            messagebox.showwarning(T("Missing shop number"), T("Please enter the shop number to reserve before saving the reservation status."))
            return

        self.manager.load_clients()
        client = self._find_client(client_name)
        if client is None:
            client = next(
                (existing for existing in self.manager.clients if existing.contact == format_contact_number(contact, DEFAULT_CONTACT_COUNTRY_CODE)),
                None,
            )

        if client is not None and str(getattr(client, "shop_number", "") or "").strip() not in {"", shop_number}:
            other_clients = [
                existing for existing in self.manager.clients
                if existing.name.strip().lower() != client_name.strip().lower()
                and str(getattr(existing, "shop_number", "") or "").strip() == shop_number
            ]
            if other_clients:
                available = self._available_shop_numbers(current_client_name=client_name)
                available_text = ", ".join(available) if available else "No available shop numbers remain"
                messagebox.showwarning(
                    T("Shop unavailable"),
                    T("Shop number '{shop}' is already assigned to another client. Available shop numbers: {available}.", shop=shop_number, available=available_text),
                )
                return

        if client is None:
            client = Client(
                client_name,
                contact,
                "Reserved",
                shop_number=shop_number,
                address="",
                notes=electrical_meter,
                electrical_meter=electrical_meter,
                reservation_status={
                    "client_name": client_name,
                    "contact": contact,
                    "shop_number": shop_number,
                    "deposit_status": deposit_status,
                    "contract_status": contract_status,
                },
            )
            self.manager.clients.append(client)
        else:
            client.name = client_name
            client.contact = format_contact_number(contact, DEFAULT_CONTACT_COUNTRY_CODE)
            client.shop_number = shop_number
            client.electrical_meter = electrical_meter or str(getattr(client, "electrical_meter", getattr(client, "notes", "")) or "")
            client.notes = client.electrical_meter
            if self.master_app is not None:
                if hasattr(self.master_app, "business_var"):
                    business = str(self.master_app.business_var.get() or "").strip()
                    if business:
                        client.business = business
                if hasattr(self.master_app, "email_var"):
                    email = str(self.master_app.email_var.get() or "").strip()
                    if email:
                        client.email = email
                if hasattr(self.master_app, "address_var"):
                    address = str(self.master_app.address_var.get() or "").strip()
                    if address:
                        client.address = address
            client.reservation_status = normalize_reservation_status({
                "client_name": client_name,
                "contact": client.contact,
                "shop_number": shop_number,
                "deposit_status": deposit_status,
                "contract_status": contract_status,
            })

        self.manager.save_clients()

        if self.master_app is not None:
            if hasattr(self.master_app, "client_name_var"):
                self.master_app.client_name_var.set(client_name)
            if hasattr(self.master_app, "contact_var"):
                self.master_app.contact_var.set(client.contact)
            if hasattr(self.master_app, "shop_number_var"):
                self.master_app.shop_number_var.set(shop_number)
            if hasattr(self.master_app, "electrical_meter_var"):
                self.master_app.electrical_meter_var.set(client.electrical_meter)
            if hasattr(self.master_app, "address_var"):
                self.master_app.address_var.set(str(getattr(client, "address", "") or ""))
            if hasattr(self.master_app, "business_var") and not str(self.master_app.business_var.get() or "").strip():
                self.master_app.business_var.set(str(getattr(client, "business", "") or ""))
            if hasattr(self.master_app, "email_var") and not str(self.master_app.email_var.get() or "").strip():
                self.master_app.email_var.set(str(getattr(client, "email", "") or ""))
            if hasattr(self.master_app, "load_client_progress"):
                self.master_app.load_client_progress(client_name, getattr(client, "business", ""))
            if hasattr(self.master_app, "refresh_client_combo"):
                self.master_app.refresh_client_combo()

        messagebox.showinfo(T("Reservation status saved"), T("Reservation status for '{name}' was saved successfully.", name=client_name))
        self.destroy()


class AllClientsProgressWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title(T("All Clients Progress"))
        self.geometry("720x440")
        self.minsize(620, 360)

        self.manager = ClientManager("clients.json")
        self.tree = ttk.Treeview(
            self,
            columns=("client", "contact", "business", "shop_number", "electrical_meter", "reservation_status", "progress", "tasks"),
            show="headings",
        )
        self.tree.heading("client", text=T("Client"))
        self.tree.heading("contact", text=T("Contact"))
        self.tree.heading("business", text=T("Business"))
        self.tree.heading("shop_number", text=T("Shop Number"))
        self.tree.heading("electrical_meter", text=T("Electrical Meter"))
        self.tree.heading("reservation_status", text=T("Reservation Status"))
        self.tree.heading("progress", text=T("Progress"))
        self.tree.heading("tasks", text="المتبقي / الإجمالي")
        self.tree.column("client", width=140, anchor="w")
        self.tree.column("contact", width=140, anchor="w")
        self.tree.column("business", width=170, anchor="w")
        self.tree.column("shop_number", width=90, anchor="center")
        self.tree.column("electrical_meter", width=120, anchor="w")
        self.tree.column("reservation_status", width=130, anchor="center")
        self.tree.column("progress", width=90, anchor="center")
        self.tree.column("tasks", width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(12, 8))

        self.tree.bind("<Double-1>", self.edit_selected_client)

        button_row = ttk.Frame(self)
        button_row.pack(pady=(0, 12))
        ttk.Button(button_row, text=T("Edit Selected Client"), command=self.edit_selected_client).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Delete Selected Client"), command=self.delete_selected_client).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Refresh"), command=self.refresh_view).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Print"), command=self.print_report).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Save Log"), command=self.export_log).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Overview"), command=self.open_overview).pack(side="left")
        self.refresh_view()

    def open_overview(self):
        self.destroy()
        app = open_overview_window()
        app.focus_section("overview")

    def go_home(self):
        self.destroy()
        open_welcome_home()

    def print_report(self):
        title = T("All Clients Progress")
        lines = [title, ""]
        self.manager.load_clients()
        for client in self.manager.clients:
            progress_info = Plan.Clients_progress.get(client.name, {})
            progress = progress_info.get("progress", 0)
            pending_tasks = progress_info.get("pending_tasks", [])
            all_tasks = progress_info.get("all_tasks", [])
            lines.append(f"{client.name} | {client.business} | {progress}% | {len(pending_tasks)} / {len(all_tasks)}")
        if not self.manager.clients:
            lines.append(T("No client selected"))
        print_report_document(title, lines)

    def export_log(self):
        ExportClientsLogWindow(self, self.manager)

    def edit_selected_client(self, event=None):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(T("No client selected"), T("Select a client row first."))
            return

        values = self.tree.item(selection[0], "values")
        if not values:
            return

        client_name = values[0]
        business = values[2] if len(values) > 2 else "N/A"

        if self.master and hasattr(self.master, "open_client_window"):
            self.master.open_client_window(client_name=client_name)
        elif self.master and hasattr(self.master, "load_client_progress"):
            self.master.load_client_progress(client_name, business)

        self.destroy()

    def delete_selected_client(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(T("No client selected"), T("Select a client row first."))
            return

        values = self.tree.item(selection[0], "values")
        if not values:
            return

        client_name = values[0]
        confirm = messagebox.askyesno(
            T("Delete client?"),
            T("Are you sure you want to delete '{client_name}' from the client list?", client_name=client_name),
        )
        if not confirm:
            return

        if self.manager.delete_client(client_name):
            Plan.Clients_progress.pop(client_name, None)
            if self.master and hasattr(self.master, "refresh_client_combo"):
                self.master.refresh_client_combo()
            if self.master and hasattr(self.master, "clear_client_form"):
                self.master.clear_client_form()
            messagebox.showinfo(T("Client deleted"), T("'{client_name}' was removed successfully.", client_name=client_name))
            self.refresh_view()
            self.lift()
            self.focus_set()
            return

        messagebox.showwarning(T("Client not found"), T("'{client_name}' was not found in the saved client list.", client_name=client_name))

    def refresh_view(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.manager.load_clients()
        all_progress = Plan.Clients_progress or {}

        seen = set()
        for client in self.manager.clients:
            seen.add(client.name)
            progress_info = all_progress.get(client.name, {})
            self.tree.insert(
                "",
                "end",
                values=build_all_clients_row_values(client, progress_info),
            )

        for client_name, progress_info in all_progress.items():
            if client_name in seen:
                continue
            pending_tasks = progress_info.get("pending_tasks", [])
            all_tasks = progress_info.get("all_tasks", [])
            self.tree.insert(
                "",
                "end",
                values=(
                    client_name,
                    "",
                    "Saved progress only",
                    "",
                    "",
                    "Not reserved",
                    f"{progress_info.get('progress', 0)}%",
                    f"{len(pending_tasks)} / {len(all_tasks)}",
                ),
            )


if __name__ == "__main__":
    safe_main()
