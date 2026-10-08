import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List

try:
    from python_code.project_paths import ensure_source_on_path
except ImportError:  # pragma: no cover - direct script fallback
    from project_paths import ensure_source_on_path

ensure_source_on_path()

from logic.shops_conversion_to_dic import format_shop_display_label
from logic.shop_management import ShopManagementMixin, normalize_shop_numbers
from logic.models.contracts import normalize_contract_details as normalize_contract_details
from logic.models.reservations import normalize_reservation_status as normalize_reservation_status
from logic.models.transactions import normalize_transaction_entry as normalize_transaction_entry
from logic.months import generate_contract_months as generate_contract_months
from logic.validations.Storage.client_storage import (
    load_clients_from_file,
    save_clients_to_file,
)

DEFAULT_CONTACT_COUNTRY_CODE = "+968"


def normalize_duration_value(value):
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    cleaned = text.lower().replace("years", "").replace("year", "").replace("yrs", "").replace("yr", "").strip()
    cleaned = cleaned.strip("()[]{} ")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", cleaned)
    if match:
        return match.group(0)
    return cleaned


def normalize_shop_value(value):
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        flattened = []
        for item in value:
            normalized = normalize_shop_value(item)
            if not normalized:
                continue
            for part in normalized.split(","):
                cleaned = part.strip()
                if cleaned and cleaned not in flattened:
                    flattened.append(cleaned)
        return ", ".join(flattened)

    if isinstance(value, dict):
        for key in ("shop_number", "shop_number_primary", "primary_shop", "selected_shop", "shop"):
            if key in value:
                return normalize_shop_value(value[key])
        return ""

    text = str(value).strip()
    if not text:
        return ""

    text = text.replace(";", ",").replace("|", ",")
    parts = [part.strip() for part in text.split(",")]
    cleaned = [part for part in parts if part]
    return ", ".join(cleaned)


def normalize_renewable_value(value):
    if value is None:
        return "Yes"

    if isinstance(value, bool):
        return "Yes" if value else "No"

    text = str(value).strip().lower()
    if not text:
        return "Yes"

    if text in {"yes", "y", "true", "1", "renewable"}:
        return "Yes"
    return "No"





def remove_shop_from_selected_shops(selected_shops, shop_number):
    target = str(shop_number or "").strip()
    if not target:
        return list(selected_shops or [])

    cleaned = []
    for entry in selected_shops or []:
        if not isinstance(entry, dict):
            cleaned.append(entry)
            continue

        shop_value = str(entry.get("Shop") or entry.get("shop") or "").strip()
        if shop_value == target:
            continue
        cleaned.append(entry)
    return cleaned


def normalize_client_progress(value):
    default_progress = {
        "client_name": "",
        "progress": 0,
        "pending_tasks": [],
        "all_tasks": [],
    }

    if not isinstance(value, dict):
        return dict(default_progress)

    normalized = dict(default_progress)
    normalized["client_name"] = str(value.get("client_name") or "")
    try:
        normalized["progress"] = int(value.get("progress", 0))
    except (TypeError, ValueError):
        normalized["progress"] = 0

    for key in ("pending_tasks", "all_tasks"):
        items = value.get(key, [])
        if isinstance(items, list):
            normalized[key] = list(items)
        elif isinstance(items, tuple):
            normalized[key] = list(items)
        else:
            normalized[key] = []

    return normalized


RESERVATION_CONTRACT_DIR_ALIASES = (
    "Reservation contract",
    "Reservation_contract",
    "Reservation Contract",
    "Reservation-Contract",
)


def _default_project_root():
    # PyInstaller onefile builds flatten "python_code/logic/..." down to a
    # top-level "logic/..." package inside the extraction temp dir, so this
    # module's __file__ sits one level shallower than it does in the source
    # tree. Using the dev-only parents[2] here would resolve to the parent of
    # the temp extraction folder (e.g. a throwaway %TEMP% directory), which
    # silently produces a brand-new, empty clients.json instead of the real
    # data. Prefer the actual executable's folder (and its parent, matching
    # this project's dist/<exe> layout) so existing client data is found;
    # fall back to the bundled seed copy in the extraction dir, and finally to
    # the plain source-tree calculation for normal (non-frozen) execution.
    if getattr(sys, "frozen", False):
        candidates = []
        exe_path = getattr(sys, "executable", None)
        if exe_path:
            exe_dir = Path(exe_path).resolve().parent
            candidates.extend([exe_dir.parent, exe_dir])
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass))

        for candidate in candidates:
            if (candidate / "clients.json").exists():
                return candidate
            for alias in RESERVATION_CONTRACT_DIR_ALIASES:
                if (candidate.parent / alias).is_dir():
                    return candidate
        if candidates:
            return candidates[0]

    return Path(__file__).resolve().parents[2]


def resolve_clients_data_path(project_root=None):
    if project_root is None:
        project_root = _default_project_root()

    project_root = Path(project_root).resolve()

    # The "Reservation contract" project is the master/source of truth for client
    # data. When it is available alongside this project (typical dev layout, with
    # both folders as siblings), read/write clients.json there instead of keeping a
    # separate local copy. Packaged builds that don't ship with a sibling
    # "Reservation contract" folder fall back to the local clients.json, which is
    # synced from the master copy at packaging time.
    parent_dir = project_root.parent
    if parent_dir.is_dir():
        for alias in RESERVATION_CONTRACT_DIR_ALIASES:
            candidate_dir = parent_dir / alias
            if candidate_dir.is_dir():
                return candidate_dir / "clients.json"

    return project_root / "clients.json"


def format_contact_number(value: str, country_code: str = DEFAULT_CONTACT_COUNTRY_CODE) -> str:
    if value is None:
        return ""

    cleaned = str(value).strip()
    if not cleaned:
        return ""

    normalized_country = str(country_code or DEFAULT_CONTACT_COUNTRY_CODE).strip()
    if not normalized_country.startswith("+"):
        normalized_country = f"+{normalized_country}"

    digits_only = "".join(ch for ch in cleaned if ch.isdigit())
    if not digits_only:
        return cleaned

    if digits_only.startswith(normalized_country.lstrip("+")):
        return f"{normalized_country}{digits_only[len(normalized_country.lstrip('+')):]}" if digits_only != normalized_country.lstrip("+") else normalized_country

    if digits_only.startswith("0"):
        return f"{normalized_country}{digits_only[1:]}"

    return f"{normalized_country}{digits_only}"


def normalize_contact(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return text
    if text.startswith("+"):
        return text
    if digits.startswith("0"):
        digits = digits[1:]
    return f"{DEFAULT_CONTACT_COUNTRY_CODE}{digits}"


def normalize_review_text(text):
    return re.sub(
        r"^\s*\d+\s*(?:[\.)\-\:\]|]\-|\-\s*)\s*",
        "",
        str(text or "").strip(),
    )





def build_clients_report_text(file_path):
    try:
        path = Path(file_path)
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except (TypeError, ValueError, OSError):
        return "Clients Log\n====================\n\nNo client data found."

    if not isinstance(payload, list):
        return "Clients Log\n====================\n\nNo client data found."

    lines = ["Clients Log", "====================", ""]
    for client_data in payload:
        if not isinstance(client_data, dict):
            continue
        name = str(client_data.get("name") or client_data.get("Client Name") or "Unknown Client").strip()
        contact = str(client_data.get("contact") or client_data.get("Contact") or "").strip()
        business = str(client_data.get("business") or client_data.get("Business") or "").strip()
        email = str(client_data.get("email") or client_data.get("Email") or "").strip()
        shop_number = client_data.get("shop_number") or client_data.get("Shop Number") or []
        normalized_shops = normalize_shop_numbers(shop_number)
        shops = ", ".join(format_shop_display_label(item) for item in normalized_shops) if normalized_shops else "N/A"
        reviews = client_data.get("reviews") or []
        contract_details = client_data.get("contract_details") or client_data.get("Contract Details") or {}

        lines.extend([
            f"Client: {name}",
            f"Contact: {contact or 'N/A'}",
            f"Business: {business or 'N/A'}",
            f"Email: {email or 'N/A'}",
            f"Shop Number(s): {shops}",
        ])

        if isinstance(contract_details, dict):
            lines.extend([
                f"Contract Number: {contract_details.get('contract_number') or contract_details.get('Contract Number') or 'N/A'}",
                f"Starting Date: {contract_details.get('starting_date') or contract_details.get('Starting Date') or 'N/A'}",
                f"Ending Date: {contract_details.get('ending_date') or contract_details.get('Ending Date') or 'N/A'}",
            ])

        if isinstance(reviews, list) and reviews:
            lines.append("Reviews:")
            for item in reviews[:5]:
                if isinstance(item, dict):
                    details = str(item.get("review") or item.get("Review") or "").strip()
                    if details:
                        lines.append(f" - {details}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"




class Client:
    def __init__(self, name: str, contact: str, business: str,
                 email: str = "", shop_number=None, reviews=None,
                 address: str = "", electrical_meter=None, notes=None,
                 contract_details=None, reservation_status=None, transactions=None):

        self.name = str(name or "").strip()
        self.contact = str(contact or "").strip()
        self.business = str(business or "").strip()
        self.email = str(email or "").strip()

        # Always store shop numbers as a clean list of numeric strings
        self.shop_number = self._normalize_shop_numbers(shop_number)

        # Common project metadata used by dashboard/contract flows
        self.address = str(address or "").strip()
        self.electrical_meter = self._normalize_meter_list(electrical_meter)
        self.notes = self._normalize_meter_list(notes)
        self.contract_details = contract_details if isinstance(contract_details, dict) else {}
        self.reservation_status = reservation_status if isinstance(reservation_status, dict) else {}
        self.transactions = [
            normalize_transaction_entry(entry)
            for entry in transactions or []
            if isinstance(entry, dict)
        ]

        # Always store reviews as a list of dicts
        self.reviews = reviews if isinstance(reviews, list) else []

    # ------------------------------------------------------------
    # Normalization Helpers
    # ------------------------------------------------------------

    @staticmethod
    def _normalize_shop_numbers(value):
        return normalize_shop_numbers(value)

    @staticmethod
    def _normalize_review_text(text):
        """Strip numbering like '1. Review', '2) Review', etc."""
        return re.sub(
            r"^\s*\d+\s*(?:[\.)\-:\]|]|\-\s*)\s*",
            "",
            str(text or "").strip()
        )

    @staticmethod
    def _normalize_meter_list(value):
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            items = []
            for item in value:
                text = str(item or "").strip()
                if text:
                    items.append(text)
            return items
        text = str(value or "").strip()
        return [text] if text else []

    # ------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------

    def to_dict(self):
        """Convert client object into JSON‑safe dictionary."""
        return {
            "name": self.name,
            "contact": self.contact,
            "business": self.business,
            "email": self.email,
            "shop_number": list(self.shop_number),  # always list
            "address": self.address,
            "electrical_meter": list(self.electrical_meter),
            "notes": list(self.notes),
            "contract_details": dict(self.contract_details) if isinstance(self.contract_details, dict) else {},
            "reservation_status": dict(self.reservation_status) if isinstance(self.reservation_status, dict) else {},
            "transactions": [
                normalize_transaction_entry(entry) for entry in self.transactions
            ],
            "reviews": list(self.reviews),          # always list of dicts
        }

    @classmethod
    def from_dict(cls, data: dict):
        """
        Safely load client from JSON dictionary.
        Handles older JSON formats gracefully.
        """
        if not isinstance(data, dict):
            return cls("", "", "", "")

        name = str(data.get("name", "")).strip()
        contact = str(data.get("contact", "")).strip()
        business = str(data.get("business", "")).strip()
        email = str(data.get("email", "")).strip()

        # Normalize shop numbers from old or new JSON formats
        shop_number = data.get("shop_number", [])
        shop_number = cls._normalize_shop_numbers(shop_number)

        # Normalize reviews
        raw_reviews = data.get("reviews", [])
        reviews = []
        if isinstance(raw_reviews, list):
            for item in raw_reviews:
                if isinstance(item, dict):
                    reviews.append({
                        "date": str(item.get("date", "")).strip(),
                        "review": cls._normalize_review_text(item.get("review", "")),
                        "comment": str(item.get("comment", "")).strip(),
                    })

        contract_details = data.get("contract_details") or data.get("Contract Details") or {}
        reservation_status = data.get("reservation_status") or data.get("Reservation Status") or {}

        return cls(
            name=name,
            contact=contact,
            business=business,
            email=email,
            shop_number=shop_number,
            reviews=reviews,
            address=str(data.get("address") or data.get("Address") or "").strip(),
            electrical_meter=data.get("electrical_meter") or data.get("Electrical Meter") or [],
            notes=data.get("notes") or data.get("Notes") or [],
            contract_details=contract_details if isinstance(contract_details, dict) else {},
            reservation_status=reservation_status if isinstance(reservation_status, dict) else {},
            transactions=data.get("transactions", []),
        )

    # ------------------------------------------------------------
    # Convenience Methods (Optional for UI)
    # ------------------------------------------------------------

    def to_vcard(self):
        """Build a vCard 3.0 text block for this client (used for copy/share)."""
        def escape(value):
            text = str(value or "")
            return (
                text.replace("\\", "\\\\")
                .replace(",", "\\,")
                .replace(";", "\\;")
                .replace("\n", "\\n")
            )

        shop_numbers = ", ".join(str(item) for item in self.shop_number if str(item).strip())
        notes_parts = []
        if shop_numbers:
            notes_parts.append(f"Shop: {shop_numbers}")
        meter_values = list(self.electrical_meter) or list(self.notes)
        if meter_values:
            notes_parts.append(f"Electrical Meter: {', '.join(meter_values)}")
        notes_text = " | ".join(notes_parts)

        lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"FN:{escape(self.name)}",
            f"N:{escape(self.name)};;;;",
        ]
        if self.contact:
            lines.append(f"TEL;TYPE=CELL:{escape(self.contact)}")
        if self.email:
            lines.append(f"EMAIL:{escape(self.email)}")
        if self.business:
            lines.append(f"ORG:{escape(self.business)}")
        if self.address:
            lines.append(f"ADR;TYPE=WORK:;;{escape(self.address)};;;;")
        if notes_text:
            lines.append(f"NOTE:{escape(notes_text)}")
        lines.append("END:VCARD")
        return "\n".join(lines) + "\n"

    def add_review(self, text: str):
        """Add a new review directly to the client."""
        review = self._normalize_review_text(text)
        if not review:
            return False

        self.reviews.append({
            "date": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "review": review,
            "comment": "",
        })
        return True

    def __repr__(self):
        return f"Client(name={self.name!r}, contact={self.contact!r})"


class ClientManager(ShopManagementMixin):
    def __init__(self, file_path=None):
        raw_path = Path(file_path).resolve() if file_path else resolve_clients_data_path()
        self.file_path = raw_path.resolve()

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("[]", encoding="utf-8")

        self.clients = []
        self.load_clients()

    # ------------------------------------------------------------
    # Core Client Operations
    # ------------------------------------------------------------

    def find_client_by_contact(self, contact: str, exclude_name: str = ""):
        normalized = normalize_contact(contact)
        exclude = (exclude_name or "").strip().lower()

        for client in self.clients:
            if client.contact == normalized and client.name.lower() != exclude:
                return client
        return None

    def add_client(self, name: str, contact: str, business: str,
                   email: str = "", shop_number=None):

        name = (name or "").strip()
        if not name:
            return False

        if self.find_client_by_contact(contact, exclude_name=name):
            return False

        shops = normalize_shop_numbers(shop_number)

        client = Client(
            name=name,
            contact=normalize_contact(contact),
            business=str(business or "").strip(),
            email=str(email or "").strip(),
            shop_number=shops,
        )

        self.clients.append(client)
        self.save_clients()
        self.create_client_directory(client)
        return True

    def upsert_client(
        self,
        *,
        client_name: str,
        contact: str = "",
        business: str = "",
        email: str = "",
        shop_number=None,
        address: str = "",
        electrical_meter=None,
        notes=None,
        contract_details=None,
        reservation_status=None,
    ):
        name = str(client_name or "").strip()
        if not name:
            raise ValueError("Client name is required.")

        normalized_contact = format_contact_number(contact or "", DEFAULT_CONTACT_COUNTRY_CODE)
        normalized_shops = normalize_shop_numbers(shop_number or [])
        normalized_meters = list(electrical_meter or [])
        contract_payload = contract_details or {}
        status_payload = reservation_status or {}

        existing = next(
            (c for c in self.clients if c.name.strip().lower() == name.lower()),
            None,
        )

        if existing is None:
            client = Client(
                name=name,
                contact=normalized_contact,
                business=str(business or "").strip(),
                email=str(email or "").strip(),
                shop_number=normalized_shops,
                address=str(address or "").strip(),
                electrical_meter=normalized_meters,
                notes=notes or normalized_meters,
                contract_details=contract_payload,
                reservation_status=status_payload,
            )
            self.clients.append(client)
            self.create_client_directory(client)
            self.save_clients()
            return client

        existing.name = name
        existing.contact = normalized_contact
        existing.business = str(business or existing.business).strip()
        existing.email = str(email or existing.email).strip()
        existing.shop_number = normalized_shops
        existing.address = str(address or existing.address).strip()
        existing.electrical_meter = normalized_meters
        existing.notes = notes or normalized_meters
        existing.contract_details = contract_payload
        existing.reservation_status = status_payload

        self.save_clients()
        return existing

    def delete_client(self, name: str):
        """Delete a single client by name (used by Overview UI)."""
        target = str(name or "").strip().lower()
        before = len(self.clients)

        self.clients = [c for c in self.clients if c.name.lower() != target]

        if len(self.clients) == before:
            return False

        self.save_clients()
        return True

    def delete_clients_bulk(self, names: list[str]):
        """
        Delete multiple selected clients (used by All Clients UI).
        Returns number of deleted clients.
        """
        normalized = {str(n).strip().lower() for n in names if str(n).strip()}
        before = len(self.clients)

        self.clients = [
            c for c in self.clients
            if c.name.lower() not in normalized
        ]

        deleted_count = before - len(self.clients)
        if deleted_count > 0:
            self.save_clients()

        return deleted_count

    # ------------------------------------------------------------
    # Review Handling
    # ------------------------------------------------------------

    def add_review(self, name: str, review_text: str):
        target = str(name or "").strip().lower()
        review = normalize_review_text(review_text)

        if not target or not review:
            return False

        client = next((c for c in self.clients if c.name.lower() == target), None)
        if client is None:
            return False

        client.reviews.append({
            "date": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "review": review,
            "comment": "",
        })

        self.save_clients()
        return True

    def update_review_comment(self, client_name: str, review_text: str,
                              comment: str, date: str = ""):

        target = str(client_name or "").strip().lower()
        review = normalize_review_text(review_text)
        comment_text = str(comment or "").strip()

        if not target or not review:
            return False

        client = next((c for c in self.clients if c.name.lower() == target), None)
        if client is None:
            return False

        # First pass: match review + date
        for item in client.reviews:
            if normalize_review_text(item.get("review")) == review:
                if not date or item.get("date") == date:
                    item["comment"] = comment_text
                    self.save_clients()
                    return True

        # Second pass: match review only
        for item in client.reviews:
            if normalize_review_text(item.get("review")) == review:
                item["comment"] = comment_text
                self.save_clients()
                return True

        return False

    def get_all_reviews(self):
        reviews = []
        for client in self.clients:
            for r in client.reviews:
                reviews.append({
                    "client_name": client.name,
                    "contact": client.contact,
                    "business": client.business,
                    "email": client.email,
                    "date": r.get("date", ""),
                    "review": r.get("review", ""),
                    "comment": r.get("comment", ""),
                })

        reviews.sort(key=lambda x: (x["date"], x["client_name"].lower()))
        return reviews

    # ------------------------------------------------------------
    # Searching
    # ------------------------------------------------------------

    def search_clients(self, keyword: str):
        key = str(keyword or "").strip().lower()
        if not key:
            return []

        results = []
        for c in self.clients:
            if (
                key in c.name.lower()
                or key in c.contact.lower()
                or key in c.business.lower()
                or key in c.email.lower()
                or any(key == s.lower() for s in c.shop_number)
            ):
                results.append(c)

        return results

    # ------------------------------------------------------------
    # Shop Number Logic (List-Based)
    # ------------------------------------------------------------

   

    def save_clients(self):
        save_clients_to_file(self.file_path, self.clients)

    def load_clients(self):
        self.clients = load_clients_from_file(self.file_path)

    # ------------------------------------------------------------
    # Export
    # ------------------------------------------------------------

    def json2txt(self):
        output = Path("docs/clients_data.txt")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps([c.to_dict() for c in self.clients], indent=2),
            encoding="utf-8"
        )
