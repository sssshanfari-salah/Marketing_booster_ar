"""Client-management actions for the main application window."""

from config import language_compat as lang
from config.language_compat import T, refresh_translatable_widgets


class ClientManagementMixin:
    """Actions shared by the main application window.

    Client details (name, contact, business, email, shop number, address,
    electrical meter) are owned exclusively by the Reservation Contract
    project; this mixin no longer creates or edits client records.
    """

    def switch_language(self, event=None):
        selected = self.language_var.get()
        lang.set_language(lang.resolve_language_code(selected))
        self.language_var.set(lang.get_language_display_label(lang.CURRENT_LANGUAGE))

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
