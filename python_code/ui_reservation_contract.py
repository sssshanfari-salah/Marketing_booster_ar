import json
import os
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from clients_management import (
    Client,
    ClientManager,
    DEFAULT_CONTACT_COUNTRY_CODE,
    format_contact_number,
    normalize_contract_details,
    normalize_duration_value,
    normalize_renewable_value,
    normalize_reservation_status,
    resolve_clients_data_path,
)
from clients_progress_ui import pick_date
from shops_conversion_to_dic import shop_meter_map
from translations import T


def normalize_python_date(value):
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""

    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw_value, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(raw_value).strftime("%d-%m-%Y")
    except ValueError:
        return raw_value


def resolve_shop_electrical_meter(shop_number):
    shop_value = str(shop_number or "").strip()
    if not shop_value:
        return ""
    return str(shop_meter_map.get(shop_value, "")).strip()

APP_ICON = None
for candidate in [
    Path(__file__).resolve().parent.parent / "starco_icon.ico",
    Path(__file__).resolve().parent / "starco_icon.ico",
]:
    if candidate.exists():
        APP_ICON = candidate
        break

if APP_ICON is None:
    APP_ICON = Path(__file__).resolve().parent.parent / "starco_icon.ico"


class ShopReservationForm(tk.Tk):
    @staticmethod
    def validate_shop_entry(shop_number, existing=None):
        existing_rows = existing or []
        shop = str(shop_number or "").strip()
        if not shop:
            return False, T("Shop number is required.")

        if not shop.isdigit():
            return False, T("Shop number must be numeric and between 1 and 36.")

        value = int(shop)
        if value < 1 or value > 36:
            return False, T("Shop number must be between 1 and 36.")

        used_numbers = {str(row[0]).strip() for row in existing_rows if row and len(row) > 0}
        if shop in used_numbers:
            return False, T("Shop number already exists in the list.")

        return True, ""

    def __init__(self, client_name=None, client_data=None, client_obj=None):
        super().__init__()
        self.title(T("Advanced Shop Reservation Form - Starco Commercial Complex"))
        self.geometry("980x760")
        self.minsize(920, 680)
        self.configure(bg="#f3f6fb")

        try:
            self.iconbitmap(str(APP_ICON))
        except tk.TclError:
            pass

        if isinstance(client_data, dict):
            self.saved_client_data = dict(client_data)
        elif client_obj is not None:
            if hasattr(client_obj, "to_dict"):
                self.saved_client_data = dict(client_obj.to_dict())
            elif isinstance(client_obj, dict):
                self.saved_client_data = dict(client_obj)
            else:
                self.saved_client_data = {}
        else:
            self.saved_client_data = self.load_saved_client_data(client_name) or {}

        self.client_name = str(
            client_name
            or self.saved_client_data.get("name")
            or self.saved_client_data.get("Client Name")
            or ""
        ).strip()
        self.client_manager = ClientManager(resolve_clients_data_path())

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Header.TLabel", background="#f3f6fb", foreground="#1f3b5b", font=("Segoe UI", 16, "bold"))
        style.configure("Section.TLabel", background="#ffffff", foreground="#1f3b5b", font=("Segoe UI", 10, "bold"))
        style.configure("Info.TLabel", background="#ffffff", foreground="#3b4a5a", font=("Segoe UI", 10))

        header = ttk.Frame(self, padding=(20, 18, 20, 10))
        header.pack(fill="x")
        header.configure(style="Card.TFrame")

        logo_frame = ttk.Frame(header)
        logo_frame.pack(side="left")
        try:
            from PIL import Image, ImageTk
            icon_path = APP_ICON
            if icon_path and icon_path.exists():
                image = Image.open(icon_path)
                if image.size[0] > 0 and image.size[1] > 0:
                    thumb = image.resize((42, 42), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(thumb)
                    ttk.Label(logo_frame, image=photo).pack(side="left", padx=(0, 12))
                    logo_frame.image = photo
        except Exception:
            pass

        title_frame = ttk.Frame(header)
        title_frame.pack(side="left", fill="x", expand=True)
        ttk.Label(title_frame, text=T("Starco Commercial Complex"), style="Header.TLabel").pack(anchor="w")
        ttk.Label(title_frame, text=T("Reservation Contract Form"), style="Info.TLabel").pack(anchor="w", pady=(2, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        self.main_tab = ttk.Frame(notebook, padding=18)
        self.shops_tab = ttk.Frame(notebook, padding=18)
        self.payment_tab = ttk.Frame(notebook, padding=18)

        notebook.add(self.main_tab, text=T("Contract Details"))
        notebook.add(self.shops_tab, text=T("Shop Information"))
        notebook.add(self.payment_tab, text=T("Payment & Bank"))

        self.create_main_tab()
        self.create_shops_tab()
        self.create_payment_tab()
        self.prefill_from_saved_client()

        button_row = ttk.Frame(self, padding=(0, 0, 0, 18))
        button_row.pack()
        ttk.Button(button_row, text=T("Save Contract"), command=self.save_contract, width=18).pack(side="left", padx=(0, 10))
        ttk.Button(button_row, text=T("Preview Contract"), command=self.preview_saved_contract, width=18).pack(side="left")

    def load_saved_client_data(self, client_name=None):
        data_file = resolve_clients_data_path()
        if not data_file.exists():
            return {}

        try:
            with data_file.open("r", encoding="utf-8") as infile:
                payload = json.load(infile)
        except (json.JSONDecodeError, OSError, TypeError):
            return {}

        if not isinstance(payload, list):
            return {}

        matches = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            if client_name:
                entry_name = str(entry.get("name") or entry.get("Client Name") or "").strip().lower()
                if entry_name != str(client_name).strip().lower():
                    continue
            if entry.get("reservation_status") or entry.get("shop_number") or entry.get("electrical_meter") or entry.get("contact") or entry.get("Contact"):
                matches.append(entry)

        if not matches:
            return {}
        return matches[-1]

    def prefill_from_saved_client(self):
        """
        Clean, unified version of prefill logic.
        Loads:
        - main contract fields
        - payment fields
        - multi-shop entries (new structure)
        """

        data = self.saved_client_data or {}

        # ---------------------------------------------------------
        # If no saved data → fill defaults
        # ---------------------------------------------------------
        if not data:
            default_contact = ""
            self.main_vars["lessor"].set("")
            self.main_vars["lessor contact"].set(default_contact)
            self.main_vars["business"].set("")
            self.main_vars["email"].set("")
            self.main_vars["address"].set("")
            self.main_vars["lessee"].set("Khalid Salim Said")
            self.main_vars["lessee contact"].set(default_contact)
            self.main_vars["date"].set(datetime.now().strftime("%d-%m-%Y"))
            self.main_vars["duration"].set("")
            self.renew_var.set("Yes")
            self.payment_vars["rent"].set("")
            self.payment_vars["deposit"].set("")
            self.payment_vars["bank"].set("01041108028002")
            self.payment_vars["holder"].set("Khalid Salim Said Al Shanfari")
            return

        # ---------------------------------------------------------
        # MAIN CLIENT FIELDS
        # ---------------------------------------------------------
        client_name = str(data.get("name") or data.get("Client Name") or "").strip()
        contact = str(data.get("contact") or data.get("Contact") or "").strip()
        business = str(data.get("business") or data.get("Business") or "").strip()
        email = str(data.get("email") or data.get("Email") or "").strip()
        address = str(data.get("address") or data.get("Address") or "").strip()

        self.main_vars["lessor"].set(client_name)
        self.main_vars["lessor contact"].set(contact)
        self.main_vars["business"].set(business)
        self.main_vars["email"].set(email)
        self.main_vars["address"].set(address)
        self.main_vars["lessee"].set("Khalid Salim Said")

        # ---------------------------------------------------------
        # CONTRACT DETAILS
        # ---------------------------------------------------------
        contract_details = data.get("contract_details", {})
        reservation_status = data.get("reservation_status", {})

        # Date
        starting_date = normalize_python_date(
            contract_details.get("starting_date") or datetime.now().strftime("%d-%m-%Y")
        )
        self.main_vars["date"].set(starting_date)

        # Duration
        duration_value = normalize_duration_value(
            contract_details.get("duration_years")
            or contract_details.get("Municipal Contract Duration")
            or contract_details.get("duration")
            or reservation_status.get("contract_duration")
            or ""
        )
        self.main_vars["duration"].set(duration_value)

        # Renewable
        renewable_value = normalize_renewable_value(contract_details.get("renewable") or "Yes")
        self.renew_var.set(renewable_value)

        # ---------------------------------------------------------
        # PAYMENT FIELDS
        # ---------------------------------------------------------
        rent_value = str(
            contract_details.get("rent_value")
            or contract_details.get("monthly_rent")
            or contract_details.get("rent")
            or reservation_status.get("rent_value")
            or ""
        ).strip()

        deposit_value = str(
            contract_details.get("security_deposit")
            or contract_details.get("deposit")
            or reservation_status.get("deposit_amount")
            or "0"
        ).strip()

        self.payment_vars["rent"].set(rent_value)
        self.payment_vars["deposit"].set(deposit_value)
        self.payment_vars["bank"].set("01041108028002")
        self.payment_vars["holder"].set("Khalid Salim Said Al Shanfari")

        # ---------------------------------------------------------
        # MULTI-SHOP LOADING (NEW CLEAN LOGIC)
        # ---------------------------------------------------------
        shops_list = data.get("shops", [])

        # Clear existing rows first (if any)
        for item in self.shop_tree.get_children():
            self.shop_tree.delete(item)

        # Load each shop entry
        for entry in shops_list:
            if not isinstance(entry, dict):
                continue

            shop = str(entry.get("Shop") or "").strip()
            meter = str(entry.get("Elec meter") or "").strip()

            if shop:
                # Auto-fill meter if missing
                if not meter:
                    meter = resolve_shop_electrical_meter(shop)

                self.add_shop(shop, meter, silent=True)

        # ---------------------------------------------------------
        # CONTACT FIELD (ensure correct binding)
        # ---------------------------------------------------------
        if contact:
            self.main_vars.setdefault("lessor contact", tk.StringVar(value=contact))
            self.main_vars["lessor contact"].set(contact)

    def create_main_tab(self):
        fields = [
            (T("Date"), "date"),
            (T("First Party (Lessor)"), "lessor"),
            (T("Contact Number"), "lessor contact"),
            (T("Business"), "business"),
            (T("Email"), "email"),
            (T("Address"), "address"),
            (T("Second Party (Lessee)"), "lessee"),
            (T("Contact Number"), "lessee contact"),
            (T("Municipal Contract Duration (Years)"), "duration"),
             ]

        self.main_vars = {}

        info_card = ttk.Frame(self.main_tab, padding=18)
        info_card.pack(fill="both", expand=True)

        ttk.Label(info_card, text=T("Contract Information"), style="Section.TLabel").pack(anchor="w", pady=(0, 12))

        for label, key in fields:
            row = ttk.Frame(info_card)
            row.pack(fill="x", pady=8)
            ttk.Label(row, text=label, width=28, anchor="w", style="Info.TLabel").pack(side="left")
            var = tk.StringVar()
            self.main_vars[key] = var
            if key == "date":
                date_frame = ttk.Frame(row)
                date_frame.pack(side="left", fill="x", expand=True)
                date_frame.columnconfigure(0, weight=1)
                ttk.Entry(date_frame, textvariable=var, width=52).grid(row=0, column=0, sticky="ew", padx=(0, 6))
                ttk.Button(date_frame, text="📅", width=3, command=lambda entry_var=var: self._pick_date(entry_var)).grid(row=0, column=1, sticky="e")
            else:
                ttk.Entry(row, textvariable=var, width=52).pack(side="left", fill="x", expand=True)

        row = ttk.Frame(info_card)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text=T("Renewable"), width=28, anchor="w", style="Info.TLabel").pack(side="left")
        self.renew_var = tk.StringVar(value="Yes")
        ttk.Combobox(row, textvariable=self.renew_var, values=["Yes", "No"], width=50, state="readonly").pack(side="left", fill="x", expand=True)

    def _pick_date(self, var):
        if pick_date is None:
            return
        current = str(var.get() or "").strip()
        selected = pick_date(self, current)
        if selected:
            var.set(normalize_python_date(selected))

    def create_shops_tab(self):
        card = ttk.Frame(self.shops_tab, padding=16)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text=T("Shop Registration"), style="Section.TLabel").pack(anchor="w", pady=(0, 12))

        self.shop_tree = ttk.Treeview(card, columns=("shop", "electricity"), show="headings", height=10)
        self.shop_tree.heading("shop", text=T("Shop Number"))
        self.shop_tree.heading("electricity", text=T("Electricity Account"))
        self.shop_tree.column("shop", width=180, anchor="center")
        self.shop_tree.column("electricity", width=220, anchor="center")
        self.shop_tree.bind("<<TreeviewSelect>>", self._on_shop_selection_changed)
        self.shop_tree.pack(fill="both", expand=True, pady=(0, 12))

        form_frame = ttk.Frame(card)
        form_frame.pack(fill="x")

        ttk.Label(form_frame, text=T("Shop Number"), width=18, anchor="w", style="Info.TLabel").grid(row=0, column=0, padx=(0, 8), pady=(0, 6), sticky="w")
        ttk.Label(form_frame, text=T("Electricity Account"), width=20, anchor="w", style="Info.TLabel").grid(row=0, column=1, padx=(0, 8), pady=(0, 6), sticky="w")

        self.shop_var = tk.StringVar()
        self.elec_var = tk.StringVar()

        self.shop_var.trace_add("write", self._sync_meter_from_shop_number)

        ttk.Entry(form_frame, textvariable=self.shop_var, width=22).grid(row=1, column=0, padx=(0, 8), sticky="ew")
        ttk.Entry(form_frame, textvariable=self.elec_var, width=22).grid(row=1, column=1, padx=(0, 8), sticky="ew")
        ttk.Button(form_frame, text=T("Add Shop"), command=self.add_shop, width=16).grid(row=1, column=2, sticky="ew")

        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(2, weight=0)

    def _sync_meter_from_shop_number(self, *args):
        shop_number = str(self.shop_var.get() or "").strip()
        if not shop_number:
            return
        meter_value = resolve_shop_electrical_meter(shop_number)
        if meter_value:
            self.elec_var.set(meter_value)

    def _on_shop_selection_changed(self, event=None):
        selected = self.shop_tree.selection()
        if not selected:
            return
        values = self.shop_tree.item(selected[0], "values")
        if not values:
            return
        self.shop_var.set(str(values[0]).strip())
        self.elec_var.set(str(values[1]).strip())

    def _get_shop_rows(self):
        rows = []
        for item in self.shop_tree.get_children():
            values = self.shop_tree.item(item, "values") or ()
            if not values:
                continue
            shop_number = str(values[0]).strip()
            elec_value = str(values[1]).strip() if len(values) > 1 else ""
            if shop_number:
                rows.append((shop_number, elec_value))
        return rows

    def _get_primary_shop_number(self):
        selected = self.shop_tree.selection()
        if selected:
            values = self.shop_tree.item(selected[0], "values") or ()
            if values and str(values[0]).strip():
                return str(values[0]).strip()

        rows = self._get_shop_rows()
        if rows:
            return rows[0][0]
        return str(self.shop_var.get().strip() or "general")

    def add_shop(self, shop_number=None, elec_value=None, silent=False):
        shop = (shop_number if shop_number is not None else self.shop_var.get()).strip()
        elec = (elec_value if elec_value is not None else self.elec_var.get()).strip()

        rows = self._get_shop_rows()
        valid, message = self.validate_shop_entry(shop, existing=rows)
        if not valid:
            if not silent:
                messagebox.showerror(T("Error"), T(message))
            return

        if not elec:
            if not silent:
                messagebox.showerror(T("Error"), T("Electricity account is required."))
            return

        manager = ClientManager(resolve_clients_data_path())
        if shop.isdigit():
            valid, _ = manager.validate_shop_number(shop)
            if not valid:
                available = manager.get_available_shop_numbers()
                if available:
                    shop = available[0]
                    if not silent:
                        messagebox.showinfo(T("Shop number updated"), T("Shop '{used}' is already assigned. The next available shop number has been selected: {suggested}.", used=shop_number or self.shop_var.get(), suggested=shop))
                else:
                    if not silent:
                        messagebox.showerror(T("Error"), T("All shop numbers from 1 to 36 are already assigned."))
                    return

        self.shop_tree.insert("", "end", values=(shop, elec))
        if not silent:
            self.shop_var.set("")
            self.elec_var.set("")

    def create_payment_tab(self):
        fields = [
            (T("Monthly Rent (OMR)"), "rent"),
            (T("Security Deposit (OMR)"), "deposit"),
            (T("Bank Account Number"), "bank"),
            (T("Account Holder"), "holder"),
        ]

        self.payment_vars = {}

        card = ttk.Frame(self.payment_tab, padding=18)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text=T("Payment Details"), style="Section.TLabel").pack(anchor="w", pady=(0, 12))

        for label, key in fields:
            row = ttk.Frame(card)
            row.pack(fill="x", pady=8)
            ttk.Label(row, text=label, width=28, anchor="w", style="Info.TLabel").pack(side="left")
            var = tk.StringVar()
            self.payment_vars[key] = var
            ttk.Entry(row, textvariable=var, width=52).pack(side="left", fill="x", expand=True)

        self.payment_vars["bank"].set("01041108028002")
        self.payment_vars["holder"].set("Khalid Salim Said Al Shanfari")

    def _get_field_value(self, key, default=""):
        var = self.main_vars.get(key)
        if var is None:
            return str(default)
        try:
            value = var.get()
        except Exception:
            return str(default)
        return str(value if value is not None else default)

    def _get_contract_output_paths(self):
        project_root = Path(__file__).resolve().parent.parent
        output_dir = project_root / "application_outputs" / "contracts"
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping_path = output_dir / "reservation_contracts.json"
        return project_root, output_dir, mapping_path

    def _get_current_shop_number(self):
        return self._get_primary_shop_number()

    def _get_contract_key(self):
        rows = self._get_shop_rows()
        if not rows:
            return "general"

        shop_numbers = [shop for shop, _ in rows]
        primary_shop = self._get_primary_shop_number()
        if len(shop_numbers) == 1:
            return shop_numbers[0]

        if primary_shop and primary_shop in shop_numbers:
            return f"{primary_shop}_{len(shop_numbers)}shops"

        normalized = "_".join(str(shop).strip() for shop in shop_numbers if str(shop).strip())
        return normalized.replace("/", "_").replace("\\", "_").replace(" ", "_")

    def _get_contract_as_text(self):
        shops = []
        for item in self.shop_tree.get_children():
            shops.append(self.shop_tree.item(item)["values"])

        lines = [
            "Starco Commercial Complex - Reservation Contract",
            "=" * 52,
            "",
            f"Date: {self.main_vars['date'].get().strip()}",
            f"First Party (Lessor): {self.main_vars['lessor'].get().strip()}",
            f"Second Party (Lessee): {self.main_vars['lessee'].get().strip()}",
            f"Municipal Contract Duration (Years): {self.main_vars['duration'].get().strip()}",
            f"Renewable: {self.renew_var.get().strip()}",
            f"Monthly Rent (OMR): {self.payment_vars['rent'].get().strip()}",
            f"Security Deposit (OMR): {self.payment_vars['deposit'].get().strip()}",
            f"Bank Account Number: {self.payment_vars['bank'].get().strip()}",
            f"Account Holder: {self.payment_vars['holder'].get().strip()}",
            "",
            "Shop Information:",
        ]

        if shops:
            for shop_number, elec_value in shops:
                lines.append(f"- Shop Number: {shop_number} | Electricity Account: {elec_value}")
        else:
            lines.append("- No shops added.")

        return "\n".join(lines) + "\n"

    def save_contract_document(self):
        _, output_dir, mapping_path = self._get_contract_output_paths()
        safe_key = self._get_contract_key()
        file_name = f"contract_{safe_key}.txt"
        target_path = output_dir / file_name
        target_path.write_text(self._get_contract_as_text(), encoding="utf-8")

        index_data = {}
        if mapping_path.exists():
            try:
                with mapping_path.open("r", encoding="utf-8") as infile:
                    payload = json.load(infile)
                if isinstance(payload, dict):
                    index_data = payload
            except (json.JSONDecodeError, OSError, TypeError):
                index_data = {}

        index_data[safe_key] = str(target_path.resolve())
        with mapping_path.open("w", encoding="utf-8") as outfile:
            json.dump(index_data, outfile, indent=2, ensure_ascii=False)

        self.last_contract_path = str(target_path.resolve())
        self.last_contract_key = safe_key
        return self.last_contract_path

    @staticmethod
    def resolve_contract_file(mapping_path, safe_key):
        if not mapping_path or not mapping_path.exists():
            return None

        try:
            with mapping_path.open("r", encoding="utf-8") as infile:
                payload = json.load(infile)
        except (json.JSONDecodeError, OSError, TypeError):
            return None

        if not isinstance(payload, dict) or safe_key not in payload:
            return None

        candidate = payload[safe_key]
        if not candidate:
            return None

        contract_path = Path(candidate)
        if not contract_path.exists():
            payload.pop(safe_key, None)
            try:
                with mapping_path.open("w", encoding="utf-8") as outfile:
                    json.dump(payload, outfile, indent=2, ensure_ascii=False)
            except (OSError, TypeError):
                pass
            return None

        return contract_path

    def preview_saved_contract(self):
        _, _, mapping_path = self._get_contract_output_paths()
        safe_key = self._get_contract_key()

        contract_path = self.resolve_contract_file(mapping_path, safe_key)
        if contract_path is None:
            target = Path(self.save_contract_document())
        else:
            target = contract_path

        if hasattr(os, "startfile"):
            os.startfile(str(target))
        elif os.name == "nt":
            subprocess.Popen(["notepad.exe", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])

    def _get_contract_details(self):
        base_details = normalize_contract_details({})
        data = {
            "contract_number": base_details.get("contract_number", ""),
            "starting_date": normalize_python_date(self.main_vars["date"].get()),
            "ending_date": "",
            "commercial_registration_number": "",
            "authorized_signature_name": self.main_vars["lessee"].get().strip(),
            "rent_value": self.payment_vars["rent"].get().strip(),
            "currency_type": "OMR",
            "open_issues": "",
            "duration_years": normalize_duration_value(self.main_vars["duration"].get()),
            "renewable": normalize_renewable_value(self.renew_var.get()),
            "first_party": self.main_vars["lessor"].get().strip(),
            "second_party": self.main_vars["lessee"].get().strip(),
        }
        base_details.update(data)
        return base_details

    def save_contract(self):
        rent_value = (self.payment_vars["rent"].get() or "").strip()
        deposit_value = (self.payment_vars["deposit"].get() or "").strip()

        try:
            if rent_value == "":
                raise ValueError("Rent is required")
            float(rent_value)
            if deposit_value == "":
                raise ValueError("Deposit is required")
            float(deposit_value)
        except ValueError:
            messagebox.showerror(T("Error"), T("Rent and Deposit must be numeric and required."))
            return

        shops = self._get_shop_rows()
        if not shops:
            messagebox.showerror(T("Error"), T("Shop number must not be empty."))
            return

        for shop_number, electricity in shops:
            if not str(shop_number or "").strip():
                messagebox.showerror(T("Error"), T("Shop number must not be empty."))
                return
            if not str(electricity or "").strip():
                messagebox.showerror(T("Error"), T("Electricity account must not be empty."))
                return

        shop_numbers = [shop_number for shop_number, _ in shops]

        contract_details = self._get_contract_details()
        contact_value = self._get_field_value("lessor contact")
        business_value = self._get_field_value("business")
        email_value = self._get_field_value("email")
        address_value = self._get_field_value("address")
        reservation_status = normalize_reservation_status(
            {
                "client_name": self.main_vars["lessor"].get().strip(),
                "contact": contact_value.strip(),
                "shop_number": shop_numbers,
                "deposit_status": "Deposite recieved" if str(self.payment_vars["deposit"].get().strip() or "0") not in {"", "0", "0.0"} else "Deposite not recieved",
                "contract_status": "completed" if str(self.payment_vars["deposit"].get().strip() or "0") not in {"", "0", "0.0"} else "under progress",
                "contract_duration": normalize_duration_value(self.main_vars["duration"].get()),
                "rent_value": self.payment_vars["rent"].get().strip(),
                "deposit_amount": self.payment_vars["deposit"].get().strip(),
            }
        )

        if not messagebox.askyesno("Confirm", "Save contract data?"):
            return

        self.client_manager.load_clients()
        client = None
        target_name = self.main_vars["lessor"].get().strip()
        if target_name:
            client = next((entry for entry in self.client_manager.clients if entry.name.strip().lower() == target_name.lower()), None)

        all_shop_numbers = [shop_number for shop_number, _ in shops]
        all_electricity = [electricity for _, electricity in shops if electricity]

        if client is None:
            client = Client(
                target_name or "Unnamed Client",
                contact_value.strip() or "",
                business_value.strip() or "Reserved",
                email=email_value.strip(),
                shop_number=all_shop_numbers,
                address=address_value.strip(),
                electrical_meter=all_electricity,
                notes=all_electricity,
                contract_details=contract_details,
                reservation_status=reservation_status,
            )
            self.client_manager.clients.append(client)
        else:
            client.name = target_name or client.name
            client.contact = format_contact_number(
                contact_value.strip() or client.contact,
                DEFAULT_CONTACT_COUNTRY_CODE,
            )
            client.business = business_value.strip() or client.business
            client.email = email_value.strip() or client.email
            client.address = address_value.strip() or client.address
            client.shop_number = all_shop_numbers
            client.electrical_meter = all_electricity
            client.notes = all_electricity
            client.contract_details = contract_details
            client.reservation_status = reservation_status

        self.client_manager.save_clients()
        self.save_contract_document()
        messagebox.showinfo(T("Saved"), T("Contract data and text file were saved successfully."))


def main():
    app = ShopReservationForm()
    app.mainloop()
    return app

