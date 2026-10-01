"""Client-management actions for the main application window."""

import tkinter as tk
from tkinter import messagebox

from config import translations as lang
from logic.clients_management import Client
from config.translations import T


class ClientManagementMixin:
    """Actions that create, save, and manage client records."""

    def save_current_client(self):
        name = self.client_name_var.get().strip()
        if not name or name == "<New Client>":
            messagebox.showwarning(T("Missing client"), T("Please enter a client name before saving."))
            return

        self.client_manager.load_clients()
        existing = next((client for client in self.client_manager.clients if client.name.lower() == name.lower()), None)
        if existing is None:
            existing = Client(name, self.contact_var.get().strip(), self.business_var.get().strip(), self.email_var.get().strip())
            self.client_manager.clients.append(existing)
        else:
            existing.contact = self.contact_var.get().strip()
            existing.business = self.business_var.get().strip()
            existing.email = self.email_var.get().strip()

        self.client_manager.save_clients()
        messagebox.showinfo(T("Client saved"), T("Client saved successfully."))

    def switch_language(self, event=None):
        selected = self.language_var.get()
        lang.set_language(selected)
        self.language_var.set(lang.CURRENT_LANGUAGE)
        self.refresh_lang_ui()


class ClientActions(ClientManagementMixin):
    pass


class ReportActions:
    pass


class StateBinding:
    pass


class TaskActions:
    pass
