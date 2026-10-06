from tkinter import messagebox

from logic.clients_management import (
    Client,
    DEFAULT_CONTACT_COUNTRY_CODE,
    format_contact_number,
    normalize_duration_value,
    normalize_reservation_status,
)
from config.translations import T


def save_contract(self):
    """
    Clean, unified save logic.
    Saves:
      - main contract fields
      - payment fields
      - multi-shop entries (new structure)
      - reservation status
      - contract details
      - updates existing client or creates new one
    """

    # ---------------------------------------------------------
    # VALIDATE RENT & DEPOSIT
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # VALIDATE SHOPS
    # ---------------------------------------------------------
    shops_rows = self._get_shop_rows()
    if not shops_rows:
        messagebox.showerror(T("Error"), T("Shop number must not be empty."))
        return

    for shop_number, electricity in shops_rows:
        if not str(shop_number).strip():
            messagebox.showerror(T("Error"), T("Shop number must not be empty."))
            return
        if not str(electricity).strip():
            messagebox.showerror(T("Error"), T("Electricity account must not be empty."))
            return

    # Convert rows → clean list of dicts
    shops_list = [
        {"Shop": shop, "Elec meter": meter}
        for shop, meter in shops_rows
    ]

    # ---------------------------------------------------------
    # CONTRACT DETAILS
    # ---------------------------------------------------------
    contract_details = self._get_contract_details()

    # ---------------------------------------------------------
    # BASIC FIELDS
    # ---------------------------------------------------------
    contact_value = self._get_field_value("lessee contact")
    business_value = self._get_field_value("business")
    email_value = self._get_field_value("email")
    address_value = self._get_field_value("address")

    # ---------------------------------------------------------
    # RESERVATION STATUS
    # ---------------------------------------------------------
    reservation_status = normalize_reservation_status(
        {
            "client_name": self.main_vars["lessee"].get().strip(),
            "contact": contact_value.strip(),
            "shops": shops_list,
            "deposit_status": (
                "Deposite recieved"
                if str(self.payment_vars["deposit"].get().strip() or "0") not in {"", "0", "0.0"}
                else "Deposite not recieved"
            ),
            "contract_status": (
                "completed"
                if str(self.payment_vars["deposit"].get().strip() or "0") not in {"", "0", "0.0"}
                else "under progress"
            ),
            "contract_duration": normalize_duration_value(self.main_vars["duration"].get()),
            "rent_value": self.payment_vars["rent"].get().strip(),
            "deposit_amount": self.payment_vars["deposit"].get().strip(),
        }
    )

    # ---------------------------------------------------------
    # CONFIRM SAVE
    # ---------------------------------------------------------
    if not messagebox.askyesno("Confirm", "Save contract data?"):
        return

    # ---------------------------------------------------------
    # LOAD CLIENTS
    # ---------------------------------------------------------
    self.client_manager.load_clients()
    client = None
    target_name = self.main_vars["lessee"].get().strip()

    if target_name:
        client = next(
            (entry for entry in self.client_manager.clients
             if entry.name.strip().lower() == target_name.lower()),
            None
        )

    # ---------------------------------------------------------
    # CREATE OR UPDATE CLIENT
    # ---------------------------------------------------------
    if client is None:
        # NEW CLIENT
        client = Client(
            target_name or "Unnamed Client",
            contact_value.strip(),
            business_value.strip() or "Reserved",
            email=email_value.strip(),
            shop_number=[entry["Shop"] for entry in shops_list],
            address=address_value.strip(),
            electrical_meter=[entry["Elec meter"] for entry in shops_list],
            notes=[entry["Elec meter"] for entry in shops_list],
            contract_details=contract_details,
            reservation_status=reservation_status,
        )

        # NEW FIELD: clean multi-shop structure
        client.shops = shops_list

        self.client_manager.clients.append(client)

    else:
        # UPDATE EXISTING CLIENT
        client.name = target_name or client.name
        client.contact = format_contact_number(
            contact_value.strip() or client.contact,
            DEFAULT_CONTACT_COUNTRY_CODE,
        )
        client.business = business_value.strip() or client.business
        client.email = email_value.strip() or client.email
        client.address = address_value.strip() or client.address

        # Legacy fields (keep for compatibility)
        client.shop_number = [entry["Shop"] for entry in shops_list]
        client.electrical_meter = [entry["Elec meter"] for entry in shops_list]
        client.notes = [entry["Elec meter"] for entry in shops_list]

        # New clean multi-shop field
        client.shops = shops_list

        client.contract_details = contract_details
        client.reservation_status = reservation_status

    # ---------------------------------------------------------
    # SAVE CLIENTS + CONTRACT DOCUMENT
    # ---------------------------------------------------------
    self.client_manager.save_clients()
    self.save_contract_document()

    messagebox.showinfo(T("Saved"), T("Contract data and text file were saved successfully."))
