"""Main application window and UI builder extracted from the monolithic controller."""

import tkinter as tk
from tkinter import ttk

from business_logic import validate_contact_number
from clients_management import ClientManager
from translations import T, CURRENT_LANGUAGE
from ui_actions.client_actions import ClientActions
from ui_actions.report_actions import ReportActions
from ui_actions.state_binding import StateBinding
from ui_actions.task_actions import TaskActions
from ui_shared import WelcomeWindow


class ProgressApp(StateBinding, TaskActions, ClientActions, ReportActions, tk.Tk):
    """Main client-progress application window."""

    def __init__(self):
        super().__init__()
        self.title(T("Client Progress Manager"))
        self.geometry("1100x720")
        self.minsize(960, 600)

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.option_add("*Font", "{Segoe UI} 8")
        self.style.configure(".", font=("Segoe UI", 8))

        self.client_manager = ClientManager("clients.json")
        self.client_manager.load_clients()
        self.plan = None

        self.client_name_var = tk.StringVar(value="")
        self.country_name_var = tk.StringVar(value="Oman")
        self.contact_var = tk.StringVar(value="")
        self.business_var = tk.StringVar(value="")
        self.shop_number_var = tk.StringVar(value="")
        self.address_var = tk.StringVar(value="")
        self.electrical_meter_var = tk.StringVar(value="")
        self.email_var = tk.StringVar(value="")
        self.review_var = tk.StringVar(value="")
        self.total_tasks_var = tk.StringVar(value="0")
        self.new_task_var = tk.StringVar(value="")
        self.progress_var = tk.StringVar(value="0%")

        self.translatable_labels = []
        self.translatable_buttons = []

        self.build_ui()
        self.clear_client_form()

    def go_home(self):
        self.destroy()
        welcome = WelcomeWindow()
        welcome.after(50, welcome.refresh_access_state)
        welcome.mainloop()

    def build_ui(self):
        main = ttk.Frame(self, padding=14)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.columnconfigure(2, weight=1)
        main.columnconfigure(3, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 8))

        title = ttk.Label(header, text=T("Client Progress Manager"), font=("Segoe UI", 14, "bold"))
        if CURRENT_LANGUAGE == "ar":
            title.pack(side="right", padx=(12, 0))
        else:
            title.pack(side="left", padx=(0, 12))
        self.translatable_labels.append((title, "Client Progress Manager"))

        lang_frame = ttk.Frame(header)
        if CURRENT_LANGUAGE == "ar":
            lang_frame.pack(side="left")
        else:
            lang_frame.pack(side="right")
        ttk.Label(lang_frame, text=T("Language")).pack(side="right" if CURRENT_LANGUAGE == "ar" else "left", padx=(0, 6))
        self.language_var = tk.StringVar(value=CURRENT_LANGUAGE)
        self.language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.language_var,
            state="readonly",
            width=10,
            values=["eng", "ar"],
        )
        self.language_combo.pack(side="left")
        self.language_combo.bind("<<ComboboxSelected>>", self.switch_language)

        details_frame = ttk.LabelFrame(main, text=T("Client Details"), padding=(10, 8))
        details_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(0, 6), pady=(0, 8))
        details_frame.columnconfigure(1, weight=1)

        ttk.Label(details_frame, text=T("Client Name")).grid(row=0, column=0, sticky="w", padx=(10, 10), pady=(8, 4))
        self.client_combo = ttk.Combobox(details_frame, textvariable=self.client_name_var, state="normal")
        self.client_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(8, 4))
        self.client_combo.bind("<<ComboboxSelected>>", self.on_client_name_selected)
        self.refresh_client_combo()

        ttk.Label(details_frame, text=T("Country")).grid(row=1, column=0, sticky="w", padx=(10, 10), pady=(0, 4))
        self.country_combo = ttk.Combobox(details_frame, textvariable=self.country_name_var, values=["Oman", "Saudi Arabia", "United Arab Emirates"], state="readonly")
        self.country_combo.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 4))

        ttk.Label(details_frame, text=T("Contact")).grid(row=2, column=0, sticky="w", padx=(10, 10), pady=(0, 4))
        ttk.Entry(details_frame, textvariable=self.contact_var, validate="key", validatecommand=(self.register(validate_contact_number), "%P")).grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=(0, 4))

        ttk.Label(details_frame, text=T("Business")).grid(row=3, column=0, sticky="w", padx=(10, 10), pady=(0, 4))
        ttk.Entry(details_frame, textvariable=self.business_var).grid(row=3, column=1, sticky="ew", padx=(0, 10), pady=(0, 4))

        ttk.Label(details_frame, text=T("Shop Number")).grid(row=4, column=0, sticky="w", padx=(10, 10), pady=(0, 4))
        ttk.Entry(details_frame, textvariable=self.shop_number_var).grid(row=4, column=1, sticky="ew", padx=(0, 10), pady=(0, 4))

        ttk.Label(details_frame, text=T("Email")).grid(row=5, column=0, sticky="w", padx=(10, 10), pady=(0, 4))
        ttk.Entry(details_frame, textvariable=self.email_var).grid(row=5, column=1, sticky="ew", padx=(0, 10), pady=(0, 8))

        review_frame = ttk.LabelFrame(main, text=T("Client Review"), padding=(10, 8))
        review_frame.grid(row=1, column=2, columnspan=2, sticky="nsew", padx=(6, 0), pady=(0, 8))
        review_frame.columnconfigure(0, weight=1)
        self.translatable_labels.append((review_frame, "Client Review"))
        self.review_text = tk.Text(review_frame, height=8, wrap="word")
        self.review_text.grid(row=0, column=0, sticky="nsew")
        self.review_text.configure(justify="left")
        self.translatable_labels.append((self.review_text, "Client Review"))

        action_row = ttk.Frame(review_frame)
        action_row.grid(row=1, column=0, sticky="e", pady=(8, 0))
        ttk.Button(action_row, text=T("Add Review")).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text=T("Save Client"), command=self.save_current_client).pack(side="left", padx=(0, 6))

        progress_box = ttk.LabelFrame(main, text=T("Progress Overview"), padding=(10, 8))
        progress_box.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        progress_box.columnconfigure(0, weight=1)
        ttk.Label(progress_box, text=T("Progress")).grid(row=0, column=0, sticky="w")
        self.progress_value_label = ttk.Label(progress_box, textvariable=self.progress_var, font=("Segoe UI", 10, "bold"))
        self.progress_value_label.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.progress_bar = ttk.Progressbar(progress_box, orient="horizontal", length=500, mode="determinate")
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        tasks_frame = ttk.LabelFrame(main, text=T("Tasks"), padding=(10, 8))
        tasks_frame.grid(row=3, column=0, columnspan=4, sticky="nsew")
        tasks_frame.columnconfigure(0, weight=1)
        tasks_frame.columnconfigure(1, weight=1)

        self.all_tasks_box = tk.Listbox(tasks_frame, height=8, exportselection=False)
        self.all_tasks_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.pending_tasks_box = tk.Listbox(tasks_frame, height=8, exportselection=False)
        self.pending_tasks_box.grid(row=0, column=1, sticky="nsew")

        buttons = ttk.Frame(tasks_frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text=T("Add Task"), command=self.add_new_task).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text=T("Refresh Progress"), command=self.refresh_display).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text=T("Home"), command=self.go_home).pack(side="left")



__all__ = ["ProgressApp"]
