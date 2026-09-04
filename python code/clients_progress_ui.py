import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote
import tkinter as tk
from tkinter import ttk, messagebox

from clients_management import Client, ClientManager

APP_ICON = Path(__file__).resolve().parent.parent / "starco_icon.ico"

TRANSLATIONS = {
    "Tkinter could not start in this environment.": "تعذر启动 واجهة Tkinter في هذا البيئة.",
    "Please run this script in a normal Windows terminal or VS Code terminal, not in a headless/debug console.": "يرجى تشغيل هذا الملف من محطة Windows عادية أو من محطة VS Code، وليس من وحدة تحكم رأسية أو وضع التصحيح.",
    "Client": "العميل",
    "Client: {client_name}": "العميل: {client_name}",
    "All Tasks": "جميع المهام",
    "Pending Tasks": "المهام المعلقة",
    "Mark Done": "تحديد كمكتمل",
    "Close": "إغلاق",
    "No task plan": "لا توجد خطة مهام",
    "There is no active task plan to update.": "لا توجد خطة مهام نشطة لتحديثها.",
    "No task selected": "لم يتم تحديد أي مهمة",
    "Select a task from the pending list first.": "حدد مهمة من القائمة المعلقة أولاً.",
    "Client Progress Manager": "مدير تقدم العملاء",
    "Client Details": "تفاصيل العميل",
    "Client Name": "اسم العميل",
    "Contact": "رقم التواصل",
    "Business": "نوع النشاط",
    "Shop Number": "رقم المحل",
    "Email": "البريد الإلكتروني",
    "Client Review": "مراجعة العميل",
    "Add Review": "إضافة مراجعة",
    "Open Review Log": "فتح سجل المراجعات",
    "Create Client Plan": "إنشاء خطة العميل",
    "Save Client": "حفظ العميل",
    "Delete Selected Client": "حذف العميل المحدد",
    "Progress Overview": "نظرة عامة على التقدم",
    "Progress": "التقدم",
    "Total Tasks": "إجمالي المهام",
    "Tasks": "المهام",
    "New task": "مهمة جديدة",
    "No client selected": "لم يتم تحديد عميل",
    "No pending tasks": "لا توجد مهام معلقة",
    "No tasks yet": "لا توجد مهام بعد",
    "No client plan": "لا توجد خطة عميل",
    "Create a client plan first.": "أنشئ خطة العميل أولاً.",
    "Missing client": "اسم العميل مفقود",
    "Please enter a client name.": "يرجى إدخال اسم العميل.",
    "Missing contact": "رقم التواصل مفقود",
    "Please enter the client contact number.": "يرجى إدخال رقم التواصل الخاص بالعميل.",
    "Missing business": "نوع النشاط مفقود",
    "Please enter the client business type.": "يرجى إدخال نوع نشاط العميل.",
    "Missing tasks": "المهام مفقودة",
    "Enter at least one task or set a total task count greater than zero.": "أدخل مهمة واحدة على الأقل أو قم بتعيين إجمالي مهام أكبر من صفر.",
    "Review saved": "تم حفظ المراجعة",
    "Review saved for '{name}'.": "تم حفظ المراجعة للعميل '{name}'.",
    "No review": "لا توجد مراجعة",
    "Please type a review before saving it.": "يرجى كتابة مراجعة قبل حفظها.",
    "Client Reviews Log": "سجل مراجعات العملاء",
    "Date": "التاريخ",
    "Review": "المراجعة",
    "No reviews yet": "لا توجد مراجعات بعد",
    "All Clients Progress": "تقدم جميع العملاء",
    "Edit Selected Client": "تعديل العميل المحدد",
    "Refresh": "تحديث",
    "Delete client?": "حذف العميل؟",
    "Are you sure you want to delete '{client_name}' from the client list?": "هل أنت متأكد أنك تريد حذف '{client_name}' من قائمة العملاء؟",
    "Client deleted": "تم حذف العميل",
    "'{client_name}' was removed successfully.": "تم حذف '{client_name}' بنجاح.",
    "Client not found": "لم يتم العثور على العميل",
    "'{client_name}' was not found in the saved client list.": "لم يتم العثور على '{client_name}' في قائمة العملاء المحفوظة.",
    "Saved progress only": "تقدم محفوظ فقط",
    "Select a client row first.": "حدد صف عميل أولاً.",
    "Select a client from the list first.": "حدد عميلًا من القائمة أولاً.",
    "Add Task": "إضافة مهمة",
    "Tasks Details": "تفاصيل المهام",
    "Refresh Progress": "تحديث التقدم",
    "Open All Clients": "فتح جميع العملاء",
    "Send Email": "إرسال بريد إلكتروني",
    "Save & Exit": "حفظ والخروج",
    "Cancel": "إلغاء",
    "Please enter a client name before saving.": "يرجى إدخال اسم العميل قبل الحفظ.",
    "Please enter the client contact number before saving.": "يرجى إدخال رقم التواصل الخاص بالعميل قبل الحفظ.",
    "Please enter the client business type before saving.": "يرجى إدخال نوع نشاط العميل قبل الحفظ.",
    "This client does not have an email saved yet.": "هذا العميل لا يحتوي على بريد إلكتروني محفوظ بعد.",
    "Select or create a client before adding a review.": "حدد عميلًا أو أنشئ عميلًا قبل إضافة مراجعة.",
    "No email": "لا يوجد بريد إلكتروني",
    "Task Details - {client_name}": "تفاصيل المهام - {client_name}",
    "<New Client>": "<عميل جديد>",
    "Select an existing client first.": "حدد عميلًا موجودًا أولاً.",
    "Client saved": "تم حفظ العميل",
    "'{name}' was saved successfully.": "تم حفظ '{name}' بنجاح.",
    "No client plan": "لا توجد خطة عميل",
    "Select a task from the pending list.": "حدد مهمة من القائمة المعلقة.",
    "No review": "لا توجد مراجعة",
    "Select or create a client before adding a review.": "حدد عميلًا أو أنشئ عميلًا قبل إضافة مراجعة.",
    "Please type a review before saving it.": "يرجى كتابة مراجعة قبل حفظها.",
    "Client not found": "لم يتم العثور على العميل",
    "No client selected": "لم يتم تحديد عميل",
    "No pending tasks": "لا توجد مهام معلقة",
    "No tasks yet": "لا توجد مهام بعد",
    "Please enter a client name before saving.": "يرجى إدخال اسم العميل قبل الحفظ.",
    "Please enter the client contact number before saving.": "يرجى إدخال رقم التواصل الخاص بالعميل قبل الحفظ.",
    "Please enter the client business type before saving.": "يرجى إدخال نوع نشاط العميل قبل الحفظ.",
}


def T(text, **kwargs):
    translated = TRANSLATIONS.get(text, text)
    if kwargs:
        return translated.format(**kwargs)
    return translated


def safe_main():
    try:
        app = ProgressApp()
        app.mainloop()
    except tk.TclError as exc:
        message = (
            T("Tkinter could not start in this environment.") + "\n\n"
            + T("Please run this script in a normal Windows terminal or VS Code terminal, not in a headless/debug console.")
            + f"\n\nDetails: {exc}"
        )
        print(message, file=sys.stderr)
        raise SystemExit(1)


def parse_task_items(raw_value, fallback_total=0):
    text = (raw_value or "").strip()
    if not text:
        if fallback_total <= 0:
            return []
        return [T("Task {i}", i=i) for i in range(1, fallback_total + 1)]
        for item in chunk.split(","):
            task = item.strip()
            if task:
                items.append(task)

    return items


class Plan:
    Clients_progress = {}

    def __init__(self, client: Client, all_tasks=None):
        self.client = client
        self.client_name = client.name
        self.all_tasks = list(all_tasks) if all_tasks else []
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
        Plan.Clients_progress[self.client.name] = {
            "client_name": self.client.name,
            "progress": self.progress,
            "pending_tasks": list(self.pending_tasks),
            "all_tasks": list(self.all_tasks),
        }

    def to_dict(self):
        return {
            "client_name": self.client_name,
            "progress": self.progress,
            "pending_tasks": list(self.pending_tasks),
            "all_tasks": list(self.all_tasks),
        }


class TaskDetailsWindow(tk.Toplevel):
    def __init__(self, master=None, client_name="Client", plan=None, all_tasks=None, pending_tasks=None):
        super().__init__(master)
        self.title(T("Task Details - {client_name}", client_name=client_name))
        self.geometry("560x430")
        self.minsize(460, 320)

        self.plan = plan
        self.master_app = master

        main = ttk.Frame(self, padding=14)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text=T("Client: {client_name}", client_name=client_name), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))

        task_columns = ttk.Frame(main)
        task_columns.pack(fill="both", expand=True)
        task_columns.columnconfigure(0, weight=1)
        task_columns.columnconfigure(1, weight=1)

        ttk.Label(task_columns, text=T("All Tasks"), font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
        ttk.Label(task_columns, text=T("Pending Tasks"), font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky="w", pady=(0, 6))

        all_scroll = ttk.Scrollbar(task_columns, orient="vertical")
        pending_scroll = ttk.Scrollbar(task_columns, orient="vertical")

        self.all_box = tk.Listbox(task_columns, height=14, exportselection=False, font=("Segoe UI", 11), yscrollcommand=all_scroll.set)
        self.pending_box = tk.Listbox(task_columns, height=14, exportselection=False, bg="#fffef5", font=("Segoe UI", 11), yscrollcommand=pending_scroll.set)

        self.all_box.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))
        all_scroll.grid(row=1, column=0, sticky="ns", padx=(0, 0), pady=(0, 10))
        self.pending_box.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(0, 10))
        pending_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 0), pady=(0, 10))

        all_scroll.config(command=self.all_box.yview)
        pending_scroll.config(command=self.pending_box.yview)

        self.populate_lists(all_tasks=all_tasks, pending_tasks=pending_tasks)

        button_row = ttk.Frame(main)
        button_row.pack(fill="x", pady=(0, 8))
        ttk.Button(button_row, text=T("Mark Done"), command=self.mark_selected_done).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Close"), command=self.close_window).pack(side="left")

    def populate_lists(self, all_tasks=None, pending_tasks=None):
        self.all_box.delete(0, tk.END)
        self.pending_box.delete(0, tk.END)

        tasks = list(all_tasks) if all_tasks is not None else []
        pending = list(pending_tasks) if pending_tasks is not None else []

        if tasks:
            for task in tasks:
                self.all_box.insert(tk.END, task)
        else:
            self.all_box.insert(tk.END, T("No tasks yet"))

        if pending:
            for task in pending:
                self.pending_box.insert(tk.END, task)
        else:
            self.pending_box.insert(tk.END, T("No pending tasks"))

    def close_window(self):
        self.destroy()
        if self.master_app is not None:
            try:
                self.master_app.deiconify()
            except Exception:
                pass

    def mark_selected_done(self):
        if self.plan is None:
            messagebox.showwarning(T("No task plan"), T("There is no active task plan to update."))
            return

        selected = self.pending_box.curselection()
        if not selected:
            messagebox.showwarning(T("No task selected"), T("Select a task from the pending list first."))
            return

        task = self.pending_box.get(selected[0])
        self.plan.complete_task(task)

        if self.master_app and hasattr(self.master_app, "refresh_display"):
            self.master_app.refresh_display()

        self.populate_lists(all_tasks=self.plan.all_tasks, pending_tasks=self.plan.pending_tasks)


class ClientReviewsLogWindow(tk.Toplevel):
    def __init__(self, master=None, manager=None):
        super().__init__(master)
        self.title(T("Client Reviews Log"))
        self.geometry("900x500")
        self.minsize(760, 360)

        self.manager = manager or ClientManager("clients.json")
        self.manager.load_clients()

        self.tree = ttk.Treeview(
            self,
            columns=("client", "business", "date", "review"),
            show="headings",
            height=18,
        )
        self.tree.heading("client", text=T("Client"))
        self.tree.heading("business", text=T("Business"))
        self.tree.heading("date", text=T("Date"))
        self.tree.heading("review", text=T("Review"))
        self.tree.column("client", width=170, anchor="w")
        self.tree.column("business", width=170, anchor="w")
        self.tree.column("date", width=160, anchor="center")
        self.tree.column("review", width=360, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(12, 8))

        self.refresh_view()

        ttk.Button(self, text=T("Close"), command=self.destroy).pack(pady=(0, 12))

    def refresh_view(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        reviews = self.manager.get_all_reviews()
        if not reviews:
            self.tree.insert("", tk.END, values=(T("No reviews yet"), "", "", ""))
            return

        for review in reviews:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    review.get("client_name", ""),
                    review.get("business", ""),
                    review.get("date", ""),
                    review.get("review", ""),
                ),
            )


class AllClientsProgressWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title(T("All Clients Progress"))
        self.geometry("720x440")
        self.minsize(620, 360)

        self.manager = ClientManager("clients.json")
        self.tree = ttk.Treeview(
            self,
            columns=("client", "business", "progress", "tasks"),
            show="headings",
        )
        self.tree.heading("client", text=T("Client"))
        self.tree.heading("business", text=T("Business"))
        self.tree.heading("progress", text=T("Progress"))
        self.tree.heading("tasks", text="المتبقي / الإجمالي")
        self.tree.column("client", width=190, anchor="w")
        self.tree.column("business", width=220, anchor="w")
        self.tree.column("progress", width=110, anchor="center")
        self.tree.column("tasks", width=150, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(12, 8))

        self.tree.bind("<Double-1>", self.edit_selected_client)

        button_row = ttk.Frame(self)
        button_row.pack(pady=(0, 12))
        ttk.Button(button_row, text=T("Edit Selected Client"), command=self.edit_selected_client).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Delete Selected Client"), command=self.delete_selected_client).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=T("Refresh"), command=self.refresh_view).pack(side="left")
        self.refresh_view()

    def edit_selected_client(self, event=None):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(T("No client selected"), T("Select a client row first."))
            return

        values = self.tree.item(selection[0], "values")
        if not values:
            return

        client_name = values[0]
        business = values[1] if len(values) > 1 else "N/A"

        if self.master and hasattr(self.master, "load_client_progress"):
            self.master.load_client_progress(client_name, business)

        self.destroy()

    def delete_selected_client(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(T("No client selected"), T("Select a client row first."))
            return

        values = self.tree.item(selection[0], "values")
        if not values:
            return

        client_name = values[0]
        confirm = messagebox.askyesno(
            T("Delete client?"),
            T("Are you sure you want to delete '{client_name}' from the client list?", client_name=client_name),
        )
        if not confirm:
            return

        if self.manager.delete_client(client_name):
            Plan.Clients_progress.pop(client_name, None)
            if self.master and hasattr(self.master, "refresh_client_combo"):
                self.master.refresh_client_combo()
            if self.master and hasattr(self.master, "clear_client_form"):
                self.master.clear_client_form()
            messagebox.showinfo(T("Client deleted"), T("'{client_name}' was removed successfully.", client_name=client_name))
            self.refresh_view()
            return

        messagebox.showwarning(T("Client not found"), T("'{client_name}' was not found in the saved client list.", client_name=client_name))

    def refresh_view(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.manager.load_clients()
        all_progress = Plan.Clients_progress or {}

        seen = set()
        for client in self.manager.clients:
            seen.add(client.name)
            progress_info = all_progress.get(client.name, {})
            progress = progress_info.get("progress", 0)
            pending_tasks = progress_info.get("pending_tasks", [])
            all_tasks = progress_info.get("all_tasks", [])
            self.tree.insert(
                "",
                "end",
                values=(
                    client.name,
                    client.business,
                    f"{progress}%",
                    f"{len(pending_tasks)} / {len(all_tasks)}",
                ),
            )

        for client_name, progress_info in all_progress.items():
            if client_name in seen:
                continue
            pending_tasks = progress_info.get("pending_tasks", [])
            all_tasks = progress_info.get("all_tasks", [])
            self.tree.insert(
                "",
                "end",
                values=(
                    client_name,
                    "Saved progress only",
                    f"{progress_info.get('progress', 0)}%",
                    f"{len(pending_tasks)} / {len(all_tasks)}",
                ),
            )


class ProgressApp(tk.Tk):
    @staticmethod
    def resolve_client_file():
        candidates = [
            Path(__file__).resolve().parent.parent / "clients.json",
            Path(__file__).resolve().parent / "clients.json",
            Path.cwd() / "clients.json",
            Path(sys.executable).resolve().parent / "clients.json",
        ]

        if getattr(sys, "_MEIPASS", None):
            candidates.insert(0, Path(sys._MEIPASS) / "clients.json")

        for candidate in candidates:
            if candidate.exists():
                return candidate

        fallback = Path(sys.executable).resolve().parent / "clients.json"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        if not fallback.exists():
            fallback.write_text("[]", encoding="utf-8")
        return fallback

    def __init__(self):
        super().__init__()
        self.title("Marketing Booster")

        if APP_ICON.exists():
            try:
                self.iconbitmap(str(APP_ICON))
            except tk.TclError:
                pass

        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.geometry(f"{max(920, self.screen_width - 180)}x{max(620, self.screen_height - 180)}")
        self.minsize(900, 560)

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.option_add("*Font", "{Segoe UI} 8")
        self.style.configure(".", font=("Segoe UI", 8))

        self.client_file = self.resolve_client_file()
        if not self.client_file.exists():
            self.client_file.parent.mkdir(parents=True, exist_ok=True)
            self.client_file.write_text("[]", encoding="utf-8")
        self.client_manager = ClientManager(self.client_file)

        self.client_name_var = tk.StringVar(value="")
        self.contact_var = tk.StringVar(value="")
        self.business_var = tk.StringVar(value="")
        self.shop_number_var = tk.StringVar(value="")
        self.email_var = tk.StringVar(value="")
        self.review_var = tk.StringVar(value="")
        self.total_tasks_var = tk.StringVar(value="0")
        self.new_task_var = tk.StringVar()

        self.plan = None
        self.client_combo = None

        self.build_ui()

    def build_ui(self):
        self.style.configure("Section.TLabelframe", padding=(10, 8), relief="groove")
        self.style.configure("Section.TLabelframe.Label", font=("Segoe UI", 8, "bold"))
        self.style.configure("Header.TLabel", font=("Segoe UI", 8, "bold"))
        self.style.configure("Action.TButton", padding=(7, 3))
        self.style.configure("Red.Horizontal.TProgressbar", background="#d32f2f", troughcolor="#e0e0e0")
        self.style.configure("Yellow.Horizontal.TProgressbar", background="#f9a825", troughcolor="#e0e0e0")
        self.style.configure("Green.Horizontal.TProgressbar", background="#2e7d32", troughcolor="#e0e0e0")

        main = ttk.Frame(self, padding=14)
        main.pack(fill="both", expand=True)

        main.columnconfigure(0, weight=25)
        main.columnconfigure(1, weight=25)
        main.columnconfigure(2, weight=20)
        main.columnconfigure(3, weight=30)
        main.rowconfigure(1, weight=1)
        main.rowconfigure(2, weight=0)
        main.rowconfigure(3, weight=1)

        title = ttk.Label(main, text=T("Client Progress Manager"), style="Header.TLabel")
        title.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        details_frame = ttk.LabelFrame(main, text=T("Client Details"), style="Section.TLabelframe")
        details_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(0, 6), pady=(0, 8))
        details_frame.columnconfigure(1, weight=1)

        ttk.Label(details_frame, text=T("Client Name")).grid(row=0, column=0, sticky="w", padx=(10, 12), pady=(8, 6))
        self.client_combo = ttk.Combobox(details_frame, textvariable=self.client_name_var, state="normal")
        self.client_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(8, 6))
        self.client_combo.bind("<<ComboboxSelected>>", self.on_client_name_selected)
        self.refresh_client_combo()

        ttk.Label(details_frame, text=T("Contact")).grid(row=1, column=0, sticky="w", padx=(10, 12), pady=(0, 6))
        self.contact_entry = ttk.Entry(details_frame, textvariable=self.contact_var)
        self.contact_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 6))

        ttk.Label(details_frame, text=T("Business")).grid(row=2, column=0, sticky="w", padx=(10, 12), pady=(0, 6))
        self.business_entry = ttk.Entry(details_frame, textvariable=self.business_var)
        self.business_entry.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=(0, 6))

        ttk.Label(details_frame, text=T("Shop Number")).grid(row=3, column=0, sticky="w", padx=(10, 12), pady=(0, 6))
        self.shop_number_entry = ttk.Entry(details_frame, textvariable=self.shop_number_var)
        self.shop_number_entry.grid(row=3, column=1, sticky="ew", padx=(0, 10), pady=(0, 6))

        ttk.Label(details_frame, text=T("Email")).grid(row=4, column=0, sticky="w", padx=(10, 12), pady=(0, 8))
        self.email_entry = ttk.Entry(details_frame, textvariable=self.email_var)
        self.email_entry.grid(row=4, column=1, sticky="ew", padx=(0, 10), pady=(0, 8))

        review_frame = ttk.LabelFrame(main, text=T("Client Review"), style="Section.TLabelframe")
        review_frame.grid(row=1, column=2, columnspan=2, sticky="nsew", padx=(6, 0), pady=(0, 8))
        review_frame.columnconfigure(0, weight=1)

        self.review_text = tk.Text(review_frame, width=30, height=4, wrap="word", font=("Segoe UI", 9))
        self.review_text.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=(8, 6))

        review_buttons = ttk.Frame(review_frame)
        review_buttons.grid(row=1, column=0, sticky="w", padx=(10, 10), pady=(0, 8))
        ttk.Button(review_buttons, text=T("Add Review"), command=self.add_client_review, style="Action.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(review_buttons, text=T("Open Review Log"), command=self.open_reviews_log, style="Action.TButton").pack(side="left")

        action_row = ttk.Frame(main)
        action_row.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)

        action_center = ttk.Frame(action_row)
        action_center.grid(row=0, column=0, columnspan=2, sticky="n")
        ttk.Button(action_center, text=T("Create Client Plan"), command=self.create_plan, style="Action.TButton", width=18).pack(side="left", padx=(0, 8))
        ttk.Button(action_center, text=T("Save Client"), command=self.save_current_client, style="Action.TButton", width=18).pack(side="left", padx=(0, 8))
        ttk.Button(action_center, text=T("Delete Selected Client"), command=self.delete_selected_client, style="Action.TButton", width=18).pack(side="left")

        progress_box = ttk.LabelFrame(main, text=T("Progress Overview"), style="Section.TLabelframe")
        progress_box.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        progress_box.columnconfigure(1, weight=1)

        ttk.Label(progress_box, text=T("Progress")).grid(row=0, column=0, sticky="w", padx=(10, 12), pady=(8, 4))
        self.progress_var = tk.StringVar(value="0%")
        ttk.Label(progress_box, textvariable=self.progress_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(8, 4))

        self.progress_bar = ttk.Progressbar(progress_box, orient="horizontal", length=500, mode="determinate")
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(10, 10), pady=(0, 10))
        self._apply_progress_bar_color(0)

        ttk.Label(progress_box, text=T("Total Tasks")).grid(row=2, column=0, sticky="w", padx=(10, 12), pady=(0, 8))
        self.total_entry = ttk.Entry(progress_box, textvariable=self.total_tasks_var, state="readonly")
        self.total_entry.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=(0, 8))

        tasks_frame = ttk.LabelFrame(main, text=T("Tasks"), style="Section.TLabelframe")
        tasks_frame.grid(row=4, column=0, columnspan=4, sticky="nsew", pady=(0, 8))
        tasks_frame.columnconfigure(0, weight=2)
        tasks_frame.columnconfigure(1, weight=0)
        tasks_frame.columnconfigure(2, weight=2)
        tasks_frame.columnconfigure(3, weight=0)
        tasks_frame.columnconfigure(4, weight=1, minsize=180)
        tasks_frame.rowconfigure(1, weight=1)

        ttk.Label(tasks_frame, text=T("All Tasks"), font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(10, 0), pady=(8, 4))
        ttk.Label(tasks_frame, text=T("Pending Tasks"), font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(10, 0), pady=(8, 4))

        list_area = ttk.Frame(tasks_frame)
        list_area.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=(10, 0), pady=(0, 8))
        list_area.columnconfigure(0, weight=2)
        list_area.columnconfigure(1, weight=0)
        list_area.columnconfigure(2, weight=2)
        list_area.columnconfigure(3, weight=0)

        all_scroll = ttk.Scrollbar(list_area, orient="vertical")
        pending_scroll = ttk.Scrollbar(list_area, orient="vertical")

        self.all_tasks_box = tk.Listbox(
            list_area,
            height=8,
            width=28,
            exportselection=False,
            bg="#ffffff",
            selectmode="browse",
            font=("Segoe UI", 10),
            yscrollcommand=all_scroll.set,
            relief="solid",
            borderwidth=1,
        )
        self.pending_tasks_box = tk.Listbox(
            list_area,
            height=8,
            width=28,
            exportselection=False,
            bg="#fffef5",
            selectmode="browse",
            font=("Segoe UI", 10),
            yscrollcommand=pending_scroll.set,
            relief="solid",
            borderwidth=1,
        )

        all_scroll.config(command=self.all_tasks_box.yview)
        pending_scroll.config(command=self.pending_tasks_box.yview)

        self.all_tasks_box.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 0))
        all_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=(0, 0))
        self.pending_tasks_box.grid(row=0, column=2, sticky="nsew", padx=(0, 4), pady=(0, 0))
        pending_scroll.grid(row=0, column=3, sticky="ns", padx=(0, 0), pady=(0, 0))

        button_row = ttk.Frame(tasks_frame)
        button_row.grid(row=1, column=4, sticky="nse", padx=(8, 10), pady=(0, 8))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)

        action_buttons = [
            (T("Add Task"), self.add_task),
            (T("Tasks Details"), self.open_task_details_window),
            (T("Refresh Progress"), self.refresh_display),
            (T("Open All Clients"), self.open_all_clients),
            (T("Send Email"), self.send_email_to_client),
            (T("Save & Exit"), self.save_and_exit),
            (T("Cancel"), self.cancel_and_exit),
        ]

        for idx, (text, command) in enumerate(action_buttons):
            column = idx % 2
            row = idx // 2
            ttk.Button(
                button_row,
                text=text,
                command=command,
                style="Action.TButton",
                width=15,
            ).grid(row=row, column=column, sticky="ew", padx=(0, 4), pady=(0, 4))

        task_entry_row = ttk.Frame(tasks_frame)
        task_entry_row.grid(row=2, column=0, columnspan=5, sticky="ew", padx=(10, 10), pady=(0, 8))
        ttk.Label(task_entry_row, text=T("New task")).pack(side="left", padx=(0, 8))
        self.new_task_entry = ttk.Entry(task_entry_row, textvariable=self.new_task_var)
        self.new_task_entry.pack(side="left", fill="x", expand=True)

        main.rowconfigure(4, weight=2)
        tasks_frame.rowconfigure(1, weight=1)

        self.clear_client_form()

    def refresh_client_combo(self):
        self.client_manager.load_clients()
        names = [client.name for client in self.client_manager.clients]
        new_client_label = T("<New Client>")
        combo_values = [new_client_label] + names
        self.client_combo.configure(values=combo_values)
        if self.client_name_var.get() in combo_values:
            self.client_combo.set(self.client_name_var.get())
        else:
            self.client_combo.set(new_client_label)

    def clear_client_form(self):
        self.plan = None
        self.client_name_var.set("")
        self.contact_var.set("")
        self.business_var.set("")
        self.shop_number_var.set("")
        self.email_var.set("")
        self.total_tasks_var.set("0")
        self.new_task_var.set("")
        self.progress_var.set("0%")
        self.progress_bar["value"] = 0
        self.progress_bar.configure(style="Red.Horizontal.TProgressbar")
        self.all_tasks_box.delete(0, tk.END)
        self.pending_tasks_box.delete(0, tk.END)
        self.all_tasks_box.insert(tk.END, T("No client selected"))
        self.pending_tasks_box.insert(tk.END, T("No pending tasks"))

    def on_client_name_selected(self, event=None):
        name = self.client_name_var.get().strip()
        if not name:
            self.clear_client_form()
            return

        if name == T("<New Client>"):
            self.clear_client_form()
            self.client_name_var.set("")
            return

        self.client_manager.load_clients()
        matching_client = next(
            (client for client in self.client_manager.clients if client.name.lower() == name.lower()),
            None,
        )

        if matching_client is None:
            self.clear_client_form()
            self.client_name_var.set(name)
            return

        self.load_client_progress(matching_client.name, matching_client.business)
        self.contact_var.set(matching_client.contact)
        self.business_var.set(matching_client.business)
        self.shop_number_var.set(matching_client.shop_number)
        self.email_var.set(matching_client.email)

    def _parse_task_list(self):
        task_text = self.new_task_var.get().strip()
        if task_text:
            return parse_task_items(task_text, fallback_total=0)

        try:
            total = int(self.total_tasks_var.get())
        except ValueError:
            total = 0

        if total <= 0:
            return []
        return [f"Task {i}" for i in range(1, total + 1)]

    def delete_selected_client(self):
        name = self.client_name_var.get().strip()
        if not name or name == T("<New Client>"):
            messagebox.showwarning(T("No client selected"), T("Select an existing client first."))
            return

        confirm = messagebox.askyesno(
            T("Delete client?"),
            T("Are you sure you want to delete '{client_name}' from the client list?", client_name=name),
        )
        if not confirm:
            return

        removed = self.client_manager.delete_client(name)
        if not removed:
            messagebox.showwarning(T("Client not found"), T("'{client_name}' was not found in the saved client list.", client_name=name))
            return

        Plan.Clients_progress.pop(name, None)
        self.refresh_client_combo()
        self.clear_client_form()
        messagebox.showinfo(T("Client deleted"), T("'{client_name}' was removed successfully.", client_name=name))

    def create_plan(self):
        name = self.client_name_var.get().strip()
        if not name:
            messagebox.showwarning(T("Missing client"), T("Please enter a client name."))
            return

        contact = self.contact_var.get().strip()
        business = self.business_var.get().strip()
        if not contact:
            messagebox.showwarning(T("Missing contact"), T("Please enter the client contact number."))
            return
        if not business:
            messagebox.showwarning(T("Missing business"), T("Please enter the client business type."))
            return

        email = self.email_var.get().strip()
        tasks = self._parse_task_list()

        if not tasks:
            messagebox.showwarning(T("Missing tasks"), T("Enter at least one task or set a total task count greater than zero."))
            return

        self.client_manager.load_clients()
        existing = next((client for client in self.client_manager.clients if client.name.lower() == name.lower()), None)
        if existing is None:
            client = Client(name, contact, business, email)
            self.client_manager.clients.append(client)
        else:
            existing.contact = contact
            existing.business = business
            existing.email = email or existing.email
            client = existing

        self.client_manager.save_clients()

        self.plan = Plan(client, all_tasks=list(tasks))
        self.plan.sync_task_lists(all_tasks=list(tasks), pending_tasks=list(tasks))
        self.total_tasks_var.set(str(len(self.plan.all_tasks)))
        self.new_task_var.set("")
        self.refresh_display()

    def open_task_details_window(self):
        if self.plan is None:
            messagebox.showwarning(T("No client plan"), T("Create a client plan first."))
            return

        TaskDetailsWindow(
            self,
            client_name=self.client_name_var.get().strip() or self.plan.client_name,
            plan=self.plan,
            all_tasks=list(self.plan.all_tasks),
            pending_tasks=list(self.plan.pending_tasks),
        )

    def add_task(self):
        if self.plan is None:
            messagebox.showwarning(T("No client plan"), T("Create a client plan first."))
            return

        task = self.new_task_var.get().strip()
        if not task:
            return

        self.plan.add_pending_task(task)
        self.refresh_display()
        self.new_task_var.set("")

    def complete_selected_task(self):
        if self.plan is None:
            return

        selected = self.pending_tasks_box.curselection()
        if not selected:
            messagebox.showwarning(T("No task selected"), T("Select a task from the pending list."))
            return

        task = self.pending_tasks_box.get(selected[0])
        self.plan.complete_task(task)
        self.refresh_display()

    def _apply_progress_bar_color(self, value):
        if value < 33:
            self.progress_bar.configure(style="Red.Horizontal.TProgressbar")
        elif value < 66:
            self.progress_bar.configure(style="Yellow.Horizontal.TProgressbar")
        else:
            self.progress_bar.configure(style="Green.Horizontal.TProgressbar")

    def refresh_display(self):
        self.all_tasks_box.delete(0, tk.END)
        self.pending_tasks_box.delete(0, tk.END)

        if self.plan is None:
            self.all_tasks_box.insert(tk.END, T("No client selected"))
            self.pending_tasks_box.insert(tk.END, T("No pending tasks"))
            return

        self.plan.sync_task_lists(all_tasks=self.plan.all_tasks, pending_tasks=self.plan.pending_tasks)
        self.progress_var.set(f"{self.plan.progress}%")
        self.progress_bar["value"] = self.plan.progress
        self._apply_progress_bar_color(self.plan.progress)
        self.total_tasks_var.set(str(len(self.plan.all_tasks)))

        if self.plan.all_tasks:
            for task in self.plan.all_tasks:
                self.all_tasks_box.insert(tk.END, task)
        else:
            self.all_tasks_box.insert(tk.END, T("No tasks yet"))

        if self.plan.pending_tasks:
            for task in self.plan.pending_tasks:
                self.pending_tasks_box.insert(tk.END, task)
        else:
            self.pending_tasks_box.insert(tk.END, T("No pending tasks"))

    def load_client_progress(self, client_name, business="N/A"):
        self.client_manager.load_clients()
        matching_client = next(
            (client for client in self.client_manager.clients if client.name.lower() == client_name.lower()),
            None,
        )

        if matching_client is not None:
            client = matching_client
            business = matching_client.business
            self.contact_var.set(matching_client.contact)
            self.business_var.set(matching_client.business)
            self.shop_number_var.set(matching_client.shop_number)
            self.email_var.set(matching_client.email)
        else:
            client = Client(client_name, "N/A", business, shop_number="")

        saved = Plan.Clients_progress.get(client_name, {})
        all_tasks = list(saved.get("all_tasks", []))

        if not all_tasks:
            default_total = self.total_tasks_var.get().strip()
            try:
                total = int(default_total) if default_total else 5
            except ValueError:
                total = 5
            all_tasks = [T("Task {i}", i=i) for i in range(1, total + 1)]

        pending_tasks = list(saved.get("pending_tasks", all_tasks))
        self.client_name_var.set(client_name)
        self.plan = Plan(client, all_tasks=all_tasks)
        self.plan.sync_task_lists(all_tasks=all_tasks, pending_tasks=pending_tasks)
        self.total_tasks_var.set(str(len(self.plan.all_tasks)))
        self.refresh_display()

    def save_current_client(self):
        self.client_manager.load_clients()
        name = self.client_name_var.get().strip()
        if not name or name == T("<New Client>"):
            messagebox.showwarning(T("Missing client"), T("Please enter a client name before saving."))
            return

        contact = self.contact_var.get().strip()
        business = self.business_var.get().strip()
        if not contact:
            messagebox.showwarning(T("Missing contact"), T("Please enter the client contact number before saving."))
            return
        if not business:
            messagebox.showwarning(T("Missing business"), T("Please enter the client business type before saving."))
            return

        existing = next(
            (client for client in self.client_manager.clients if client.name.lower() == name.lower()),
            None,
        )

        shop_number = self.shop_number_var.get().strip()

        if existing is None:
            client = Client(
                name,
                contact,
                business,
                self.email_var.get().strip(),
                shop_number=shop_number,
            )
            self.client_manager.clients.append(client)
        else:
            existing.contact = contact
            existing.business = business
            existing.shop_number = shop_number
            existing.email = self.email_var.get().strip() or existing.email
            client = existing

        self.client_manager.save_clients()
        self.refresh_client_combo()
        self.client_name_var.set(name)

        if self.plan is None:
            self.plan = Plan(client, all_tasks=[])
        self.plan.client = client
        self.plan.client_name = client.name
        self.plan.update_clients_progress()
        self.refresh_display()
        messagebox.showinfo(T("Client saved"), T("'{name}' was saved successfully.", name=name))

    def send_email_to_client(self):
        email = self.email_var.get().strip()
        if not email:
            messagebox.showwarning(T("No email"), T("This client does not have an email saved yet."))
            return

        gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={quote(email)}"
        if webbrowser.open(gmail_url):
            return

        mailto_url = f"mailto:{quote(email)}"
        webbrowser.open(mailto_url)

    def save_and_exit(self):
        self.save_current_client()
        self.destroy()

    def cancel_and_exit(self):
        self.destroy()

    def add_client_review(self):
        name = self.client_name_var.get().strip()
        if not name or name == T("<New Client>"):
            messagebox.showwarning(T("No client selected"), T("Select or create a client before adding a review."))
            return

        review = self.review_text.get("1.0", "end").strip()
        if not review:
            messagebox.showwarning(T("No review"), T("Please type a review before saving it."))
            return

        if not self.client_manager.add_review(name, review):
            messagebox.showwarning(T("Client not found"), T("'{client_name}' was not found in the saved client list.", client_name=name))
            return

        self.review_text.delete("1.0", tk.END)
        messagebox.showinfo(T("Review saved"), T("Review saved for '{name}'.", name=name))

    def open_reviews_log(self):
        self.client_manager.load_clients()
        ClientReviewsLogWindow(self, self.client_manager)

    def open_all_clients(self):
        AllClientsProgressWindow(self)


if __name__ == "__main__":
    safe_main()
