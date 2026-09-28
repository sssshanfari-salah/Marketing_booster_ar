"""Domain and business rules for the client manager UI and task logic."""

import calendar
import json
import re
from datetime import datetime
from pathlib import Path

from clients_management import Client
from translations import T


def normalize_country_code(code):
    if code is None:
        return "+968"
    cleaned = str(code).strip()
    if not cleaned:
        return "+968"
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
        return "", "Oman"
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return "", "Oman"
    for code, country in {
        "+968": "Oman",
        "+966": "Saudi Arabia",
        "+971": "United Arab Emirates",
        "+974": "Qatar",
        "+965": "Kuwait",
        "+973": "Bahrain",
        "+962": "Jordan",
        "+20": "Egypt",
        "+1": "United States",
        "+44": "United Kingdom",
        "+49": "Germany",
        "+33": "France",
    }.items():
        if digits.startswith(code.lstrip("+")):
            local = digits[len(code.lstrip("+")):]
            return (local.lstrip("0") if local else "", country)
    if digits.startswith("968"):
        local = digits[3:]
        return (local.lstrip("0") if local else "", "Oman")
    if digits.startswith("0"):
        return (digits[1:], "Oman")
    return digits, "Oman"


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
    candidate = Path(__file__).resolve().parent / "country_codes.json"
    if candidate.exists():
        try:
            with candidate.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    return fallback


def load_shop_electrical_meter_map():
    meters_path = Path(__file__).resolve().parent / "Shops_Elect_meters.json"
    mapping = {}
    if not meters_path.exists():
        return mapping
    try:
        with meters_path.open("r", encoding="utf-8") as handle:
            entries = json.load(handle)
    except (json.JSONDecodeError, OSError, TypeError):
        return mapping
    if not isinstance(entries, list):
        return mapping
    for item in entries:
        if not isinstance(item, dict):
            continue
        shop_value = str(item.get("Shop") or item.get("shop") or item.get("shop_number") or "").strip()
        meter_value = str(item.get("Elec meter") or item.get("Elec Meter") or item.get("electrical_meter") or item.get("meter") or "").strip()
        if shop_value and meter_value:
            mapping[shop_value] = meter_value
    return mapping


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


class Plan:
    Clients_progress = {}

    def __init__(self, client: Client, all_tasks=None):
        self.client = client
        self.client_name = client.name
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


def generate_contract_months(start_date=None, end_date=None):
    start_value = str(start_date or "").strip()
    end_value = str(end_date or "").strip()
    if not start_value and not end_value:
        return []

    def parse_date(value):
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    start_dt = parse_date(start_value)
    end_dt = parse_date(end_value)
    if start_dt is None and end_dt is not None:
        start_dt = end_dt.replace(day=1)
    if end_dt is None and start_dt is not None:
        end_dt = start_dt.replace(day=28)
    if start_dt is None or end_dt is None:
        return []
    if end_dt < start_dt:
        start_dt, end_dt = end_dt, start_dt

    months = []
    current = start_dt.replace(day=1)
    while current <= end_dt:
        months.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    seen = set()
    unique_months = []
    for month in months:
        if month in seen:
            continue
        seen.add(month)
        unique_months.append(month)
    return unique_months


class DatePickerPopup:
    """Small helper retained for UI modules that wish to open a calendar popup."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Move this class to ui_windows.py for the actual Tkinter implementation.")


__all__ = [
    "Plan",
    "generate_contract_months",
    "normalize_country_code",
    "format_task_entry",
    "strip_task_number_prefix",
    "validate_contact_number",
    "parse_contact_for_ui",
    "load_country_codes",
    "load_shop_electrical_meter_map",
    "parse_task_items",
    "DatePickerPopup",
]
