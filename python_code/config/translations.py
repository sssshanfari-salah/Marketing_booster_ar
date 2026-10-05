"""Translation resources and i18n helpers for the client manager UI."""

import re

try:
    from python_code.project_paths import ensure_source_on_path
except ImportError:  # pragma: no cover - direct script fallback
    from project_paths import ensure_source_on_path

ensure_source_on_path()

try:
    import arabic_reshaper
except ModuleNotFoundError:
    arabic_reshaper = None

try:
    from bidi.algorithm import get_display
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    def get_display(value):
        return value

# Shared language state.
CURRENT_LANGUAGE = "eng"


TRANSLATIONS = {
    "eng": {
        "Client": "Client",
        "Client Details": "Client Details",
        "Client Name": "Client Name",
        "Country": "Country",
        "Contact": "Contact Number",
        "Business": "Business",
        "Shop Number": "Shop Number",
        "Address": "Address",
        "Electrical Meter": "Electrical Meter",
        "Email": "Email",
        "Review": "Review",
        "Add Review": "Add Review",
        "Add Client": "Add Client",
        "Save Client": "Save Client",
        "Delete Selected Client": "Delete Selected Client",
        "Select All": "Select All",
        "Delete clients?": "Delete clients?",
        "Delete client?": "Delete client?",
        "Progress Overview": "Progress Overview",
        "Progress": "Progress",
        "Tasks": "Tasks",
        "All Tasks": "All Tasks",
        "Pending Tasks": "Pending Tasks",
        "Task Details": "Task Details",
        "New task": "New task",
        "Add Task": "Add Task",
        "Save": "Save",
        "Close": "Close",
        "Home": "Home",
        "Transactions": "Transactions",
        "Payment Report": "Payment Report",
        "Print": "Print",
        "Save Log": "Save Log",
        "Language": "Language",
        "English": "English",
        "العربية": "العربية",
        "Guest": "Guest",
        "Rent Calculator": "Rent Calculator",
        "Reservation Contract": "Reservation Contract",
        "Reservation Contract Form": "Reservation Contract Form",
        "Advanced Shop Reservation Form - Starco Commercial Complex": "Advanced Shop Reservation Form - Starco Commercial Complex",
        "Starco Commercial Complex": "Starco Commercial Complex",
        "Saved Reservation Contracts": "Saved Reservation Contracts",
        "Search": "Search",
        "Preview": "Preview",
        "Print": "Print",
        "Contract Details": "Contract Details",
        "Shop Information": "Shop Information",
        "Payment & Bank": "Payment & Bank",
        "Save Contract": "Save Contract",
        "Preview Contract": "Preview Contract",
        "Contract Information": "Contract Information",
        "Renewable": "Renewable",
        "Shop Registration": "Shop Registration",
        "Electricity Account": "Electricity Account",
        "Add Shop": "Add Shop",
        "Payment Details": "Payment Details",
        "Monthly Rent (OMR)": "Monthly Rent (OMR)",
        "Security Deposit (OMR)": "Security Deposit (OMR)",
        "Bank Account Number": "Bank Account Number",
        "Account Holder": "Account Holder",
        "Date": "Date",
        "First Party (Lessor)": "First Party (Lessor)",
        "Second Party (Lessee)": "Second Party (Lessee)",
        "Municipal Contract Duration (Years)": "Municipal Contract Duration (Years)",
        "Error": "Error",
        "Both fields are required.": "Both fields are required.",
        "Rent and Deposit must be numeric.": "Rent and Deposit must be numeric.",
        "Saved": "Saved",
        "Contract data and text file were saved successfully.": "Contract data and text file were saved successfully.",
        "Please select a saved contract first.": "Please select a saved contract first.",
        "The selected contract file could not be found.": "The selected contract file could not be found.",
        "Unable to open contract: {exc}": "Unable to open contract: {exc}",
        "Unable to print contract: {exc}": "Unable to print contract: {exc}",
        "All Clients Progress": "All Clients Progress",
        "Export Clients Log": "Export Clients Log",
        "Export Task Log": "Export Task Log",
        "Export Review Log": "Export Review Log",
        "Client Reviews Log": "Client Reviews Log",
        "Overview": "Overview",
        "Exit": "Exit",
        "User Profile": "User Profile",
        "User Name": "User Name",
        "User Email": "User Email",
        "Register": "Register",
        "Login": "Login",
        "Logout": "Logout",
        "Save User": "Save User",
        "User Login": "User Login",
        "User Registration": "User Registration",
        "Cansel": "Cansel",
        "Logged in as: {user_name}": "Logged in as: {user_name}",
        "Login successful. Access granted to the app.": "Login successful. Access granted to the app.",
        "You have logged out and returned to guest access.": "You have logged out and returned to guest access.",
        "Please enter your user name.": "Please enter your user name.",
        "Please enter your email address.": "Please enter your email address.",
        "User profile saved successfully.": "User profile saved successfully.",
        "User profile confirmed successfully.": "User profile confirmed successfully.",
        "User registered successfully. Please log in with your saved credentials.": "User registered successfully. Please log in with your saved credentials.",
        "User registered successfully.": "User registered successfully.",
        "User not found. Access granted as guest. Transactions, contract details, and email sending stay restricted.": "User not found. Access granted as guest. Transactions, contract details, and email sending stay restricted.",
        "User not found in the saved user list. Please register first or continue as guest.": "User not found in the saved user list. Please register first or continue as guest.",
        "Report issued by: {user_name}": "Report issued by: {user_name}",
        "Project Manager To-Do": "Project Manager To-Do",
        "Open client payment records": "Open client payment records",
        "No reviews yet": "No reviews yet",
    },
    "ar": {
        "Client": "العميل",
        "Client Details": "تفاصيل العميل",
        "Client: {client_name}": "العميل: {client_name}",
        "Task Details - {client_name}": "تفاصيل المهمة - {client_name}",
        "Client Name": "اسم العميل",
        "Country": "الدولة",
        "Contact": "رقم التواصل",
        "Business": "نوع النشاط",
        "Shop Number": "رقم المحل",
        "Address": "العنوان",
        "Electrical Meter": "عداد الكهرباء",
        "Email": "البريد الإلكتروني",
        "Review": "المراجعة",
        "Add Review": "إضافة مراجعة",
        "Add Client": "إضافة عميل",
        "Save Client": "حفظ العميل",
        "Delete Selected Client": "حذف العميل المحدد",
        "Select All": "تحديد الكل",
        "Delete clients?": "حذف العملاء؟",
        "Delete client?": "حذف العميل؟",
        "Progress Overview": "نظرة عامة على التقدم",
        "Progress": "التقدم",
        "Tasks": "المهام",
        "All Tasks": "جميع المهام",
        "Pending Tasks": "المهام المعلقة",
        "Task Details": "تفاصيل المهمة",
        "New task": "مهمة جديدة",
        "Add Task": "إضافة مهمة",
        "Save": "حفظ",
        "Close": "إغلاق",
        "Home": "الرئيسية",
        "Transactions": "المعاملات",
        "Payment Report": "تقرير الدفع",
        "Print": "طباعة",
        "Save Log": "حفظ السجل",
        "Language": "اللغة",
        "English": "English",
        "العربية": "العربية",
        "Guest": "ضيف",
        "Rent Calculator": "حاسبة الإيجار",
        "Reservation Contract": "عقد الحجز",
        "Reservation Contract Form": "نموذج عقد الحجز",
        "Advanced Shop Reservation Form - Starco Commercial Complex": "نموذج الحجز المتقدم - مجمع ستاركو التجاري",
        "Starco Commercial Complex": "مجمع ستاركو التجاري",
        "Saved Reservation Contracts": "العقود المحفوظة",
        "Search": "بحث",
        "Preview": "معاينة",
        "Print": "طباعة",
        "Contract Details": "تفاصيل العقد",
        "Shop Information": "معلومات المحل",
        "Payment & Bank": "الدفع والبنك",
        "Save Contract": "حفظ العقد",
        "Preview Contract": "معاينة العقد",
        "Contract Information": "معلومات العقد",
        "Renewable": "قابل للتجديد",
        "Shop Registration": "تسجيل المحل",
        "Electricity Account": "حساب الكهرباء",
        "Add Shop": "إضافة محل",
        "Payment Details": "تفاصيل الدفع",
        "Monthly Rent (OMR)": "الإيجار الشهري (أومر)",
        "Security Deposit (OMR)": "الأمانة (أومر)",
        "Bank Account Number": "رقم الحساب البنكي",
        "Account Holder": "اسم صاحب الحساب",
        "Date": "التاريخ",
        "First Party (Lessor)": "الطرف الأول (المؤجر)",
        "Second Party (Lessee)": "الطرف الثاني (المستأجر)",
        "Municipal Contract Duration (Years)": "مدة العقد البلدي (سنوات)",
        "Error": "خطأ",
        "Both fields are required.": "يجب إدخال الحقلين.",
        "Rent and Deposit must be numeric.": "يجب أن يكون الإيجار والأمانة رقمين.",
        "Saved": "تم الحفظ",
        "Contract data and text file were saved successfully.": "تم حفظ بيانات العقد وملف النص بنجاح.",
        "Please select a saved contract first.": "يرجى اختيار عقد محفوظ أولاً.",
        "The selected contract file could not be found.": "تعذر العثور على ملف العقد المحدد.",
        "Unable to open contract: {exc}": "تعذر فتح العقد: {exc}",
        "Unable to print contract: {exc}": "تعذر طباعة العقد: {exc}",
        "All Clients Progress": "تقدم جميع العملاء",
        "Export Clients Log": "تصدير سجل العملاء",
        "Export Task Log": "تصدير سجل المهام",
        "Export Review Log": "تصدير سجل المراجعات",
        "Client Reviews Log": "سجل مراجعات العملاء",
        "Overview": "نظرة عامة",
        "Exit": "خروج",
        "User Profile": "ملف المستخدم",
        "User Name": "اسم المستخدم",
        "User Email": "بريد المستخدم",
        "Register": "تسجيل",
        "Login": "تسجيل الدخول",
        "Logout": "تسجيل الخروج",
        "Save User": "حفظ المستخدم",
        "User Login": "تسجيل الدخول",
        "User Registration": "تسجيل المستخدم",
        "Cansel": "إلغاء",
        "Logged in as: {user_name}": "تم تسجيل الدخول كـ: {user_name}",
        "Login successful. Access granted to the app.": "تم تسجيل الدخول بنجاح. تم منح الوصول للتطبيق.",
        "You have logged out and returned to guest access.": "تم تسجيل الخروج والعودة إلى الوصول كضيف.",
        "Please enter your user name.": "يرجى إدخال اسم المستخدم.",
        "Please enter your email address.": "يرجى إدخال البريد الإلكتروني.",
        "User profile saved successfully.": "تم حفظ ملف المستخدم بنجاح.",
        "User profile confirmed successfully.": "تم تأكيد ملف المستخدم بنجاح.",
        "User registered successfully. Please log in with your saved credentials.": "تم تسجيل المستخدم بنجاح. يرجى تسجيل الدخول باستخدام بياناتك المحفوظة.",
        "User registered successfully.": "تم تسجيل المستخدم بنجاح.",
        "User not found. Access granted as guest. Transactions, contract details, and email sending stay restricted.": "لم يتم العثور على المستخدم. تم منح الوصول كضيف. المعاملات وتفاصيل العقد وإرسال البريد الإلكتروني تبقى مقيدة.",
        "User not found in the saved user list. Please register first or continue as guest.": "لم يتم العثور على المستخدم في القائمة المحفوظة. يرجى التسجيل أولاً أو المتابعة كضيف.",
        "Report issued by: {user_name}": "تم إصدار التقرير من قبل: {user_name}",
        "Project Manager To-Do": "مدير المشاريع - المهام",
        "Open client payment records": "فتح سجلات الدفع للعميل",
        "No reviews yet": "لا توجد مراجعات بعد",
    },
}


def is_arabic_text(value):
    text = str(value or "")
    return any(
        0x0600 <= ord(ch) <= 0x06FF
        or 0x0750 <= ord(ch) <= 0x077F
        or 0x08A0 <= ord(ch) <= 0x08FF
        or 0xFB50 <= ord(ch) <= 0xFDFF
        or 0xFE70 <= ord(ch) <= 0xFEFF
        for ch in text
    )


def apply_bidi_text(value):
    text = str(value or "")
    if not text:
        return ""

    if not is_arabic_text(text):
        return text

    normalized = text.strip()
    if not normalized:
        return text

    placeholder_free = re.sub(r"\{[^}]*\}", " ", normalized)
    if re.search(r"[A-Za-z]", placeholder_free):
        return normalized

    if arabic_reshaper is None:
        return normalized

    return arabic_reshaper.reshape(normalized)


def set_language(lang):
    global CURRENT_LANGUAGE
    code = str(lang or "eng").strip().lower()
    CURRENT_LANGUAGE = "ar" if code in {"ar", "arabic"} else "eng"
    return CURRENT_LANGUAGE


def T(text, **kwargs):
    language_map = TRANSLATIONS.get(CURRENT_LANGUAGE, TRANSLATIONS["eng"])
    translated = language_map.get(text, text)
    if kwargs:
        translated = translated.format(**kwargs)
    return translated


def validate_translation_coverage():
    english_keys = set(TRANSLATIONS.get("eng", {}).keys())
    arabic_keys = set(TRANSLATIONS.get("ar", {}).keys())
    missing = sorted(key for key in english_keys if key not in arabic_keys)
    if missing:
        raise ValueError(
            "Missing Arabic translations for UI labels:\n" + "\n".join(f" - {key}" for key in missing[:50])
        )
    return None
