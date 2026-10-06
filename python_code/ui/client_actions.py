"""Client-management actions for the main application window."""

import tkinter as tk
from tkinter import messagebox

from config import translations as lang
from config.translations import T, refresh_translatable_widgets
from logic.clients_management import Client, ClientManager, resolve_clients_data_path


class ClientManagementMixin:
    """Actions that create, save, and manage client records."""

    def save_current_client(self):
        if not hasattr(self, "client_manager"):
            self.client_manager = ClientManager(resolve_clients_data_path())

        name = str(getattr(self, "client_name_var", None).get() if hasattr(self, "client_name_var") else "").strip()
        if not name or name == T("<New Client>"):
            messagebox.showwarning(T("Missing client"), T("Please enter a client name before saving."))
            return

        contact = str(getattr(self, "contact_var", None).get() if hasattr(self, "contact_var") else "").strip()
        business = str(getattr(self, "business_var", None).get() if hasattr(self, "business_var") else "").strip()
        email = str(getattr(self, "email_var", None).get() if hasattr(self, "email_var") else "").strip()
        shop_number = str(getattr(self, "shop_number_var", None).get() if hasattr(self, "shop_number_var") else "").strip()
        address = str(getattr(self, "address_var", None).get() if hasattr(self, "address_var") else "").strip()
        electrical_meter = str(getattr(self, "electrical_meter_var", None).get() if hasattr(self, "electrical_meter_var") else "").strip()

        self.client_manager.load_clients()
        existing = next((client for client in self.client_manager.clients if client.name.lower() == name.lower()), None)

        if existing is None:
            existing = Client(
                name,
                contact,
                business,
                email=email,
                shop_number=shop_number,
                address=address,
                notes=electrical_meter,
            )
            self.client_manager.clients.append(existing)
        else:
            existing.contact = contact
            existing.business = business
            existing.email = email
            existing.shop_number = shop_number
            existing.address = address
            existing.notes = electrical_meter

        self.client_manager.save_clients()
        messagebox.showinfo(T("Client saved"), T("Client saved successfully."))

    def switch_language(self, event=None):
        selected = self.language_var.get()
        lang.set_language(selected)
        self.language_var.set(lang.CURRENT_LANGUAGE)

        if hasattr(self, "refresh_lang_ui"):
            self.refresh_lang_ui()
            return

        if hasattr(self, "translatable_labels") or hasattr(self, "translatable_buttons"):
            refresh_translatable_widgets(self)


class ClientActions(ClientManagementMixin):
    pass


class ReportActions:
    pass


class StateBinding:
    pass


class TaskActions:
    pass
