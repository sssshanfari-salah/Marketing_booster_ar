import tkinter as tk
from tkinter import ttk, messagebox

from config.translations import T
from logic.clients_management import ClientManager, resolve_clients_data_path
from logic.finance_manager import FinanceManager
from logic.validations.payment_rules import normalize_payment_method
from logic.months import get_previous_month
from ui.treeview_positioning import position_widget_in_column


class ClientTransactionsWindow(tk.Toplevel):
    PAYMENT_METHOD_CHOICES = ("Cash", "Cheque", "Bank Transaction")

    def __init__(self, master=None, client_name: str = ""):
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

        ttk.Label(header_fields, text=f"{T('Client')}:", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
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
        for column, title in zip(
            columns,
            [
                T("Month"),
                T("Status"),
                T("Amount"),
                T("Payment Method"),
                T("Cheque Number"),
                T("Due Date"),
                T("Bank Name"),
                T("Bank Transaction Details"),
            ],
        ):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=120, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind(
            "<Configure>",
            lambda event: (
                self._position_status_checkbuttons(),
                self._position_method_comboboxes(),
                self._position_cheque_entries(),
                self._position_bank_transaction_entries(),
                self._position_amount_entries(),
                self._position_due_date_entries(),
                self._position_due_date_buttons(),
                self._position_bank_name_entries(),
                self._position_month_comboboxes(),
            ),
        )

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

    def go_home(self):
        from ui.dashboard import open_welcome_home

        self.destroy()
        open_welcome_home()

    def _list_client_names(self):
        self.manager.load_clients()
        return [client.name for client in self.manager.clients if getattr(client, "name", "").strip()]

    def _find_client(self, client_name: str):
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
        self.month_options = self.finance.get_month_options() if self.finance else []
        self.refresh_view()

    def add_transaction_row(self):
        if self.client is None or self.finance is None:
            messagebox.showwarning(T("No client"), T("Select a client before adding transactions."))
            return

        month_value = self.month_options[0] if self.month_options else ""
        new_tx = self.finance.add_transaction_for_month(month_value)
        self.refresh_view()

    def save_transactions(self):
        if self.client is None:
            messagebox.showwarning(T("No client"), T("No client selected to save transactions."))
            return
        self.manager.save_clients()
        messagebox.showinfo(T("Saved"), T("Transactions saved successfully."))

    def refresh_view(self):
        self.month_options = self.finance.get_month_options() if self.finance else []

        for item in self.tree.get_children():
            self.tree.delete(item)

        for mapping in (
            self.status_checkbuttons,
            self.method_comboboxes,
            self.cheque_entries,
            self.bank_transaction_entries,
            self.amount_entries,
            self.due_date_entries,
            self.due_date_buttons,
            self.bank_name_entries,
            self.month_comboboxes,
        ):
            for row_id, widget in list(mapping.items()):
                widget.destroy()
            mapping.clear()

        self.status_vars.clear()
        self.method_vars.clear()
        self.cheque_vars.clear()
        self.bank_transaction_vars.clear()
        self.amount_vars.clear()
        self.due_date_vars.clear()
        self.bank_name_vars.clear()
        self.month_vars.clear()

        if self.client is None or self.finance is None:
            self.tree.insert("", "end", values=(T("No client selected"), "", "", "", "", "", "", ""))
            return

        transactions = list(self.finance.transactions)
        if not transactions:
            self.tree.insert("", "end", values=(T("No payments yet"), "", "", "", "", "", "", ""))
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
                lambda event, current_row=row_id, current_entry=entry, current_var=month_var: self._update_month(
                    current_row, current_entry, current_var
                ),
            )
            self.month_comboboxes[row_id] = month_combo

            checkbox_var = tk.BooleanVar(value=self.finance.is_completed(entry))
            self.status_vars[row_id] = checkbox_var
            checkbutton = tk.Checkbutton(
                self.tree,
                variable=checkbox_var,
                command=lambda current_row=row_id, current_entry=entry, current_var=checkbox_var: self._toggle_status(
                    current_row, current_entry, current_var
                ),
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
                lambda event, current_row=row_id, current_entry=entry, current_var=method_var: self._update_payment_method(
                    current_row, current_entry, current_var
                ),
            )
            self.method_comboboxes[row_id] = combobox

            cheque_var = tk.StringVar(value=str(entry.get("cheque_number", "")))
            self.cheque_vars[row_id] = cheque_var
            cheque_entry = ttk.Entry(self.tree, textvariable=cheque_var, width=12)
            self.cheque_entries[row_id] = cheque_entry

            bank_tx_var = tk.StringVar(value=str(entry.get("bank_transaction_details", "")))
            self.bank_transaction_vars[row_id] = bank_tx_var
            bank_tx_entry = ttk.Entry(self.tree, textvariable=bank_tx_var, width=14)
            self.bank_transaction_entries[row_id] = bank_tx_entry

            amount_var = tk.StringVar(value=str(entry.get("amount", "")))
            self.amount_vars[row_id] = amount_var
            amount_entry = ttk.Entry(self.tree, textvariable=amount_var, width=10)
            self.amount_entries[row_id] = amount_entry

            due_date_var = tk.StringVar(value=str(entry.get("due_date", "")))
            self.due_date_vars[row_id] = due_date_var
            due_date_entry = ttk.Entry(self.tree, textvariable=due_date_var, width=12)
            self.due_date_entries[row_id] = due_date_entry

            bank_name_var = tk.StringVar(value=str(entry.get("bank_name", "")))
            self.bank_name_vars[row_id] = bank_name_var
            bank_name_entry = ttk.Entry(self.tree, textvariable=bank_name_var, width=14)
            self.bank_name_entries[row_id] = bank_name_entry

        self._position_status_checkbuttons()
        self._position_method_comboboxes()
        self._position_cheque_entries()
        self._position_bank_transaction_entries()
        self._position_amount_entries()
        self._position_due_date_entries()
        self._position_bank_name_entries()
        self._position_month_comboboxes()

    def _update_month(self, row_id, entry, var):
        new_month = str(var.get() or "").strip()
        self.finance.update_month(entry, new_month)
        self.tree.set(row_id, "month", entry["month"])
        coerced_due_date = entry.get("due_date", "")
        self.tree.set(row_id, "due_date", coerced_due_date)
        if row_id in self.due_date_vars:
            self.due_date_vars[row_id].set(coerced_due_date)

    def _update_payment_method(self, row_id, entry, var):
        self.finance.update_payment_method(entry, var.get())
        self.tree.set(row_id, "method", entry["payment_method"])

        cheque_entry = self.cheque_entries.get(row_id)
        if cheque_entry is not None:
            if entry["payment_method"] == "Cheque":
                cheque_entry.configure(state="normal")
            else:
                self.cheque_vars[row_id].set(entry["cheque_number"])
                cheque_entry.configure(state="disabled")

        bank_detail_entry = self.bank_transaction_entries.get(row_id)
        if bank_detail_entry is not None:
            if entry["payment_method"] == "Bank Transaction":
                bank_detail_entry.configure(state="normal")
            else:
                self.bank_transaction_vars[row_id].set(entry["bank_transaction_details"])
                bank_detail_entry.configure(state="disabled")

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
                messagebox.showwarning(
                    T("Outstanding payment"),
                    T(
                        "Complete the previous month payment for '{month}' before marking this payment as paid.",
                        month=prior_month,
                    ),
                )
            else:
                messagebox.showwarning(
                    T("Incomplete payment"),
                    T("Complete the required payment details before marking this month as paid."),
                )
            return

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
            checkbutton.place(
                x=x + 4,
                y=y + 2,
                width=max(18, width - 8),
                height=max(18, height - 4),
            )

    def _position_method_comboboxes(self):
        position_widget_in_column(self.tree, self.method_comboboxes, "method", x_offset=2, min_width=120)

    def _position_cheque_entries(self):
        position_widget_in_column(self.tree, self.cheque_entries, "cheque", x_offset=2, min_width=90)

    def _position_bank_transaction_entries(self):
        position_widget_in_column(self.tree, self.bank_transaction_entries, "bank_transaction_detail", x_offset=2, min_width=110)

    def _position_amount_entries(self):
        position_widget_in_column(self.tree, self.amount_entries, "amount", x_offset=2, min_width=90)

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
            entry_widget.place(
                x=x + 2,
                y=y + 2,
                width=max(92, width - 34),
                height=max(22, height - 4),
            )

    def _position_bank_name_entries(self):
        position_widget_in_column(self.tree, self.bank_name_entries, "bank", x_offset=2, min_width=110)

    def _position_month_comboboxes(self):
        position_widget_in_column(self.tree, self.month_comboboxes, "month", x_offset=2, min_width=110)
