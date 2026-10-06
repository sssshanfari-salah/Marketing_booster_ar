"""Shared payment normalization, reports, and finance windows."""

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from config.translations import T
from logic.clients_management import ClientManager, resolve_clients_data_path
from logic.shops_conversion_to_dic import resolve_shop_electrical_meter
from logic.shop_management import normalize_shop_numbers
from logic.models.contracts import normalize_contract_details as normalize_contract_details
from logic.models.reservations import normalize_reservation_status as normalize_reservation_status
from logic.models.transactions import normalize_transaction_entry as normalize_transaction_entry
from logic.finance_manager import FinanceManager
from logic.months import get_month_index, get_previous_month
from logic.validations.payment_rules import (
    normalize_payment_method,
)
from ui.treeview_positioning import position_widget_in_column

class ClientTransactionsWindow(tk.Toplevel):
    PAYMENT_METHOD_CHOICES = ("Cash", "Cheque", "Bank Transaction")

    def __init__(self, master=None, client_name=""):
        from logic.clients_management import ClientManager

        super().__init__(master)
        self.title(T("Client Transactions"))
        self.geometry("980x560")
        self.minsize(780, 420)
        self.master_app = master
        self.client_name = str(client_name or "").strip()
        self.manager = getattr(master, "client_manager", None)
        if self.manager is None:
            self.manager = ClientManager(resolve_clients_data_path())
        self.manager.load_clients()

        self.client = self._find_client(self.client_name) if self.client_name else None
        if self.client is None and self.master_app is not None and hasattr(self.master_app, "client_name_var"):
            determined = str(self.master_app.client_name_var.get() or "").strip()
            self.client_name = determined
            self.client = self._find_client(determined)

        self.finance = FinanceManager(self.client) if self.client is not None else None
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
        self.month_options = self.finance.get_month_options() if self.finance else []

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
        from ui.dashboard import close_popup_and_return

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
        self.finance = FinanceManager(self.client) if self.client is not None else None
        self.refresh_view()

    def go_home(self):
        from ui.dashboard import open_welcome_home

        self.destroy()
        open_welcome_home()

    def _position_status_checkbuttons(self):
        position_widget_in_column(
            self.tree,
            self.status_checkbuttons,
            "status",
            x_offset=4,
            min_width=18,
            width_adjustment=8,
            min_height=18,
        )

    def _position_method_comboboxes(self):
        position_widget_in_column(
            self.tree,
            self.method_comboboxes,
            "method",
            x_offset=2,
            min_width=120,
            width_adjustment=6,
        )

    def _position_cheque_entries(self):
        position_widget_in_column(
            self.tree,
            self.cheque_entries,
            "cheque",
            x_offset=2,
            min_width=90,
            width_adjustment=6,
        )

    def _position_bank_transaction_entries(self):
        position_widget_in_column(
            self.tree,
            self.bank_transaction_entries,
            "bank_transaction_detail",
            x_offset=2,
            min_width=110,
            width_adjustment=6,
        )

    def _position_amount_entries(self):
        position_widget_in_column(
            self.tree,
            self.amount_entries,
            "amount",
            x_offset=2,
            min_width=90,
            width_adjustment=6,
        )

    def _position_due_date_entries(self):
        position_widget_in_column(
            self.tree,
            self.due_date_entries,
            "due_date",
            x_offset=2,
            min_width=92,
            width_adjustment=34,
        )

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
        position_widget_in_column(
            self.tree,
            self.bank_name_entries,
            "bank",
            x_offset=2,
            min_width=110,
            width_adjustment=6,
        )

    def _position_month_comboboxes(self):
        position_widget_in_column(
            self.tree,
            self.month_comboboxes,
            "month",
            x_offset=2,
            min_width=110,
            width_adjustment=6,
        )

    def _toggle_status(self, row_id, entry, var):
        completed = bool(var.get())
        success = self.finance.mark_status(entry, completed)
        self.tree.set(row_id, "status", entry["status"])
        if not completed:
            return

        if not success:
            var.set(False)
            prior_month = get_previous_month(entry.get("month", ""), self.month_options)
            if prior_month:
                messagebox.showwarning(T("Outstanding payment"), T("Complete the previous month payment for '{month}' before marking this payment as paid.", month=prior_month))
            else:
                messagebox.showwarning(T("Incomplete payment"), T("Complete the required payment details before marking this month as paid."))
            return

    def _update_month(self, row_id, entry, var):
        self.finance.update_month(entry, var.get())
        self.tree.set(row_id, "month", entry["month"])

        self.tree.set(row_id, "due_date", entry["due_date"])
        if row_id in self.due_date_vars:
            self.due_date_vars[row_id].set(entry["due_date"])

    def _update_payment_method(self, row_id, entry, var):
        self.finance.update_payment_method(entry, var.get())
        self.tree.set(row_id, "method", entry["payment_method"])

        cheque_entry = self.cheque_entries.get(row_id)
        if cheque_entry is not None:
            if entry["payment_method"] == "Cheque":
                cheque_entry.configure(state="normal")
            else:
                self.cheque_vars[row_id].set("")
                cheque_entry.configure(state="disabled")

        bank_detail_entry = self.bank_transaction_entries.get(row_id)
        if bank_detail_entry is not None:
            if entry["payment_method"] == "Bank Transaction":
                bank_detail_entry.configure(state="normal")
            else:
                self.bank_transaction_vars[row_id].set("")
                bank_detail_entry.configure(state="disabled")

    def refresh_view(self):
        self.month_options = self.finance.get_month_options() if self.finance else []

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
                    normalize_payment_method(entry.get("payment_method", "Cash")),
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

            checkbox_var = tk.BooleanVar(value=self.finance.is_completed(entry))
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

            method_var = tk.StringVar(value=normalize_payment_method(entry.get("payment_method", "Cash")))
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
            if normalize_payment_method(entry.get("payment_method", "Cash")) != "Cheque":
                cheque_entry.configure(state="disabled")

            bank_transaction_var = tk.StringVar(value=str(entry.get("bank_transaction_details", "")))
            self.bank_transaction_vars[row_id] = bank_transaction_var
            bank_transaction_entry = ttk.Entry(self.tree, textvariable=bank_transaction_var, width=14)
            bank_transaction_entry.bind("<FocusOut>", lambda event, current_row=row_id, current_entry=entry, current_var=bank_transaction_var: self._update_bank_transaction_details(current_row, current_entry, current_var))
            self.bank_transaction_entries[row_id] = bank_transaction_entry
            if normalize_payment_method(entry.get("payment_method", "Cash")) != "Bank Transaction":
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
        from ui.dashboard import pick_date

        selected = pick_date(self, var.get())
        if not selected:
            return
        normalized = self.finance.update_due_date(entry if entry is not None else {}, selected)
        var.set(normalized)
        self.tree.set(row_id, "due_date", normalized)
        if row_id in self.due_date_vars:
            self.due_date_vars[row_id].set(normalized)

    def _update_due_date(self, row_id, entry, var):
        value = str(var.get() or "").strip()
        normalized = self.finance.update_due_date(entry, value)
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

        current_index = get_month_index(last_month, self.month_options)
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
        self.finance.add_transaction_for_month(month_value)
        self.refresh_view()

    def save_transactions(self):
        if self.client is None:
            messagebox.showwarning(T("No client selected"), T("Select a client from the list first."))
            return

        completed_rows = []
        rows = list(zip(self.tree.get_children(), self.client.transactions))
        for row_id, entry in rows:
            if row_id in self.month_vars:
                self.finance.update_month(entry, self.month_vars[row_id].get())
            if row_id in self.amount_vars:
                entry["amount"] = str(self.amount_vars[row_id].get() or "").strip()
            if row_id in self.cheque_vars:
                entry["cheque_number"] = str(self.cheque_vars[row_id].get() or "").strip()
            if row_id in self.due_date_vars:
                entry["due_date"] = str(self.due_date_vars[row_id].get() or "").strip()
            if row_id in self.bank_name_vars:
                entry["bank_name"] = str(self.bank_name_vars[row_id].get() or "").strip()
            if row_id in self.bank_transaction_vars:
                entry["bank_transaction_details"] = str(self.bank_transaction_vars[row_id].get() or "").strip()

            if row_id in self.method_vars:
                self.finance.update_payment_method(entry, self.method_vars[row_id].get())
        for row_id, entry in rows:
            completed = bool(self.status_vars[row_id].get()) if row_id in self.status_vars else self.finance.is_completed(entry)
            if self.finance.mark_status(entry, completed):
                completed_rows.append(entry)
            elif completed:
                if row_id in self.status_vars:
                    self.status_vars[row_id].set(False)
                messagebox.showwarning(T("Incomplete payment"), T("Complete the required payment details before marking this month as paid."))

        self.manager.load_clients()
        for existing in self.manager.clients:
            if existing.name.lower() == self.client.name.lower():
                existing.transactions = [
                    {key: value.strip() for key, value in transaction.to_dict().items()}
                    for transaction in self.finance.normalize_all_transactions()
                ]
                break
        self.manager.save_clients()

        if completed_rows:
            month_name = str(completed_rows[-1].get("month", "") or "").strip() or "this month"
            messagebox.showinfo(T("Payment completed"), f"Payment for {month_name} has been marked as successfully completed.")

        messagebox.showinfo(T("Transactions saved"), T("Client payment transactions were updated successfully."))
        self.refresh_view()

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
        from logic.clients_management import ClientManager

        super().__init__(master)
        self.title(T("Reservation Status"))
        self.geometry("500x360")
        self.minsize(420, 300)
        self.master_app = master
        self.manager = getattr(master, "client_manager", None)
        if self.manager is None:
            self.manager = ClientManager(resolve_clients_data_path())

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
            if var is self.shop_number_var:
                shop_combo = ttk.Combobox(
                    main,
                    textvariable=var,
                    values=self._available_shop_numbers(
                        current_client_name=self.client_name_var.get()
                    ),
                    state="readonly",
                    width=28,
                )
                shop_combo.bind("<FocusIn>", self._refresh_shop_number_options)
                shop_combo.grid(row=row_index, column=1, sticky="ew", pady=(0, 8))
            else:
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
        self.manager.load_clients()
        return self.manager.get_available_shop_numbers(exclude_name=current_client_name)

    def _refresh_shop_number_options(self, event=None):
        if event is not None:
            event.widget.configure(
                values=self._available_shop_numbers(
                    current_client_name=self.client_name_var.get()
                )
            )

    def save_status(self):
        from logic.clients_management import (
            Client,
            DEFAULT_CONTACT_COUNTRY_CODE,
            format_contact_number,
        )

        from tkinter import messagebox

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

        exclude_name = client.name if client is not None else client_name
        valid_shop, shop_error = self.manager.validate_shop_number(
            shop_number,
            exclude_name=exclude_name,
        )
        if not valid_shop:
            available = self._available_shop_numbers(current_client_name=exclude_name)
            available_text = ", ".join(available) if available else "No available shop numbers remain"
            messagebox.showwarning(
                T("Shop unavailable"),
                T(
                    "Shop number '{shop}' is unavailable: {error}. Available shop numbers: {available}.",
                    shop=shop_number,
                    error=shop_error,
                    available=available_text,
                ),
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
            client.shop_number = normalize_shop_numbers(shop_number)
            if electrical_meter:
                client.electrical_meter = [electrical_meter]
                client.notes = [electrical_meter]
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
                self.master_app.electrical_meter_var.set(electrical_meter)
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
