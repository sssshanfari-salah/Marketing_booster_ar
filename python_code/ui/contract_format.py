from __future__ import annotations

import html
from pathlib import Path

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

CONTRACT_CONDITIONS = (
    "• The second party is fully responsible for obtaining all approvals and permits required "
    "by the concerned authorities to conduct their business in the shops of the first party. "
    "The first party bears no responsibility toward the second party or any third party after "
    "signing this agreement and receiving the security deposit, in case the second party fails "
    "to obtain the required approvals or permits.\n\n"
    "• The official municipal lease contract will be for one year only, renewable.\n\n"
    "• A cash cheque equal to one month’s total rent must be submitted upon signing this "
    "contract as a security deposit and to begin the municipal lease procedures.\n\n"
    "• If the lessee withdraws for any reason after signing this contract, the paid security "
    "deposit is non-refundable.\n\n"
    "• The lessor will install the partition between the shops after the municipal lease "
    "contract is approved.\n\n"
    "• If the lessee complies with the contract, the paid amount will be kept as a security "
    "deposit and will be returned to the lessee at the end of the lease contract, provided the "
    "shop(s) are returned in the same condition as received, with no outstanding dues or remarks.\n\n"
    "• Monthly rent cheques and the security deposit cheque must be submitted after signing "
    "this contract and before signing the official municipal lease contract.\n\n"
    "God is the Grantor of success.\n"
)


def _resolve_logo_path():
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / "icons" / "starco_icon2.ico",
        base_dir / "icons" / "Starco_icon2.ico",
        base_dir / "icons" / "starco_icon.ico",
        base_dir / "icons" / "Starco_icon.ico",
        base_dir / "starco_icon2.ico",
        base_dir / "Starco_icon2.ico",
        base_dir / "starco_icon.ico",
        base_dir / "Starco_icon.ico",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _normalize_contract_data(contract_data):
    if not isinstance(contract_data, dict):
        contract_data = {}

    details = contract_data.get("details") or []
    detail_map = {}
    for label, value in details:
        key = str(label or "").strip().lower()
        if key:
            detail_map[key] = str(value or "").strip()

    title = str(contract_data.get("title") or "Starco Commercial Complex - Reservation Contract").strip()
    shops = contract_data.get("shops") or []
    shop_numbers = ", ".join(str(shop or "").strip() for shop, _ in shops if str(shop or "").strip())
    electricity_numbers = ", ".join(str(elec or "").strip() for _, elec in shops if str(elec or "").strip())

    def get_value(*keys):
        for key in keys:
            value = detail_map.get(key)
            if value:
                return value
        return ""

    return {
        "title": title,
        "date": get_value("date") or contract_data.get("date") or "",
        "lessor": get_value("first party (lessor)", "lessor") or "",
        "lessee": get_value("second party (lessee)", "lessee") or "",
        "shop_numbers": shop_numbers or "N/A",
        "electricity_numbers": electricity_numbers or "N/A",
        "rent": get_value("monthly rent (omr)", "rent") or contract_data.get("rent") or "",
        "deposit": get_value("security deposit (omr)", "deposit") or contract_data.get("deposit") or "",
        "account_number": get_value("bank account number", "bank") or contract_data.get("bank") or "01041108028002",
        "account_holder": get_value("account holder", "holder") or contract_data.get("holder") or "Khalid Salem Said Al-Shanfari",
        "conditions": str(contract_data.get("conditions") or CONTRACT_CONDITIONS).strip(),
    }


def _detect_contract_language(language=None, contract_data=None):
    if isinstance(contract_data, dict):
        for key in ("language", "contract_language", "version", "lang", "contract_version"):
            if contract_data.get(key) is not None:
                language = contract_data.get(key)
                break

    if language is None:
        return "english"

    normalized = str(language).strip().lower().replace("_", "-")
    if normalized in {"ar", "arabic", "arab", "rtl", "arabic-version", "arabic_version"}:
        return "arabic"
    if normalized in {"both", "bilingual", "english-arabic", "en-ar", "ar-en", "dual", "all", "english+arabic", "english-ar", "arabic-english"}:
        return "both"
    return "english"


def _build_bilingual_contract_preview_html(contract_data=None):
    try:
        from python_code.ui.contract_format_ar import build_arabic_contract_preview_html
    except ImportError:  # pragma: no cover - direct script fallback
        from ui.contract_format_ar import build_arabic_contract_preview_html

    english_doc = _build_english_contract_preview_html(contract_data)
    arabic_doc = build_arabic_contract_preview_html(contract_data)

    english_body = english_doc.split("<body>", 1)[1].split("</body>", 1)[0]
    arabic_body = arabic_doc.split("<body>", 1)[1].split("</body>", 1)[0]

    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Shop Reservation Contract - English & Arabic</title>
  <style>
    body {{
      margin: 0;
      background: #eef2f7;
      font-family: Arial, Helvetica, sans-serif;
      color: #1d1d1d;
    }}
    .dual-layout {{
      display: flex;
      flex-direction: column;
      gap: 28px;
      padding: 24px;
    }}
    .lang-panel {{
      background: #fff;
      border: 1px solid #e2e8f0;
      overflow: hidden;
      page-break-inside: avoid;
      break-inside: avoid;
    }}
    .lang-header {{
      background: #f8fafc;
      color: #123d69;
      padding: 14px 18px;
      font-size: 20px;
      font-weight: bold;
      text-align: center;
      border-bottom: 1px solid #e2e8f0;
    }}
    .lang-body {{
      padding: 0;
    }}
    @media print {{
      body {{
        background: #fff;
      }}
      .dual-layout {{
        padding: 0;
        gap: 0;
      }}
      .lang-panel {{
        border: none;
        box-shadow: none;
        margin: 0;
        page-break-before: always;
        break-before: page;
      }}
      .lang-panel:first-child {{
        page-break-before: auto;
        break-before: auto;
      }}
      .lang-header {{
        background: #fff;
        color: #123d69;
        border-bottom: 1px solid #dfe5ec;
        margin: 0 0 12px 0;
        padding: 4px 0 10px 0;
      }}
      .lang-body {{
        margin: 0;
      }}
      .lang-body .page {{
        box-shadow: none;
        margin: 0;
        width: auto;
        min-height: auto;
        padding: 0;
      }}
    }}
  </style>
</head>
<body>
  <div class="dual-layout">
    <div class="lang-panel">
      <div class="lang-header">English Version</div>
      <div class="lang-body">{english_body}</div>
    </div>
    <div class="lang-panel" dir="rtl">
      <div class="lang-header">الإصدار العربي</div>
      <div class="lang-body" dir="rtl">{arabic_body}</div>
    </div>
  </div>
</body>
</html>
""".format(english_body=english_body, arabic_body=arabic_body)


def _build_english_contract_preview_html(contract_data=None):
    payload = _normalize_contract_data(contract_data)
    logo_path = _resolve_logo_path()
    logo_html = ""
    if logo_path and logo_path.exists():
        logo_url = logo_path.resolve().as_uri()
        logo_html = (
            '<div class="brand-block">'
            '<img src="{logo_url}" alt="Starco logo" class="brand-logo" />'
            '<div class="brand-copy"><div class="brand-name">STARCO COMMERCIAL COMPLEX</div>'
            '<div class="brand-tag">Shop Reservation Contract</div></div>'
            '</div>'
        ).format(logo_url=html.escape(str(logo_url), quote=False))

    rent_value = payload["rent"]
    rent_text = (
        f"It has been agreed between both parties to reserve the above-mentioned shops for the above-mentioned lessee "
        f"for a monthly rent amount of {rent_value or '...........'} OMR for the shops, according to the following conditions:"
    )

    conditions = payload["conditions"].replace("\r\n", "\n").replace("\r", "\n")
    date_value = payload["date"] or "__________"
    deposit_value = payload["deposit"] or "__________"

    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    @page {{ size: A4; margin: 18mm; }}
    body {{
      margin: 0;
      background: #f0f2f5;
      font-family: Arial, Helvetica, sans-serif;
      color: #1d1d1d;
      line-height: 1.55;
    }}
    .page {{
      width: min(92vw, 820px);
      min-height: auto;
      margin: 12mm auto;
      padding: 16mm;
      box-sizing: border-box;
      background: #ffffff;
      box-shadow: 0 8px 22px rgba(0, 0, 0, 0.08);
    }}
    .brand-block {{
      display: flex;
      align-items: center;
      gap: 14px;
      padding-bottom: 10px;
      border-bottom: 2px solid #dfe5ec;
      margin-bottom: 16px;
    }}
    .brand-logo {{
      width: 96px;
      height: 96px;
      object-fit: contain;
      border-radius: 14px;
      background: #f0f2f5;
      padding: 8px;
      box-sizing: border-box;
    }}
    .brand-copy {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .brand-name {{
      font-size: 22px;
      color: #123d69;
      font-weight: bold;
    }}
    .brand-tag {{
      font-size: 13px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #53657b;
    }}
    h1 {{
      display: none;
    }}
    .meta {{
      margin: 14px 0 10px;
      font-size: 14px;
      font-weight: bold;
    }}
    .party-block {{
      margin-top: 10px;
      font-size: 16px;
      display: grid;
      gap: 8px;
    }}
    .rent-text {{
      margin: 18px 0 10px;
      font-size: 16px;
      text-align: left;
    }}
    .conditions-box {{
      margin-top: 8px;
      border: 1px solid #dfe5ec;
      background: #fafcff;
      padding: 14px 16px;
      font-size: 15px;
      white-space: pre-line;
    }}
    .row {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      margin-top: 18px;
      font-size: 15px;
    }}
    .signature-row {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      margin-top: 26px;
      font-size: 15px;
      min-height: 90px;
    }}
    .signature-box {{
      width: 46%;
      border-top: 1px solid #cfd8e3;
      padding-top: 8px;
      min-height: 70px;
    }}
    .bank-block {{
      margin-top: 18px;
      font-size: 12px;
      line-height: 1.7;
      white-space: pre-line;
      color: #3b4857;
    }}
    @media print {{
      body {{ background: #ffffff; }}
      .page {{
        width: auto;
        min-height: auto;
        margin: 0;
        padding: 0;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    {logo_html}
    <h1>Shop Reservation Contract</h1>

    <div class="meta"><strong>Date:</strong> {date}</div>

    <div class="party-block">
      <div><strong>First Party (Lessor):</strong> {lessor}</div>
      <div><strong>Second Party (Lessee):</strong> {lessee}</div>
      <div><strong>Shop Numbers:</strong> {shop_numbers}</div>
      <div><strong>Electricity Account Numbers:</strong> {electricity_numbers}</div>
    </div>

    <div class="rent-text">{rent_text}</div>

    <div class="conditions-box">{conditions}</div>

    <div class="signature-row">
      <div class="signature-box"><strong>Signature of First Party (Lessor):</strong></div>
      <div class="signature-box"><strong>Signature &amp; Stamp of Second Party (Lessee):</strong></div>
    </div>

    <div class="row">
      <div><strong>Security Deposit Received:</strong> {deposit} OMR</div>
    </div>

    <div class="bank-block">For bank transfer:
Bank Dhofar – Account Number: {account_number}
Or via mobile name: KHALID9770@BDAF
Account Name: {account_holder}</div>
  </div>
</body>
</html>
""".format(
        title=html.escape(str(payload["title"]), quote=False),
        logo_html=logo_html,
        date=html.escape(date_value, quote=False),
        lessor=html.escape(payload["lessor"] or "__________", quote=False),
        lessee=html.escape(payload["lessee"] or "__________", quote=False),
        shop_numbers=html.escape(payload["shop_numbers"], quote=False),
        electricity_numbers=html.escape(payload["electricity_numbers"], quote=False),
        rent_text=html.escape(rent_text, quote=False),
        conditions=html.escape(conditions, quote=False),
        deposit=html.escape(deposit_value, quote=False),
        account_number=html.escape(payload["account_number"], quote=False),
        account_holder=html.escape(payload["account_holder"], quote=False),
    )


def build_contract_preview_html(contract_data=None, language=None):
    mode = _detect_contract_language(language=language, contract_data=contract_data)
    if mode == "arabic":
        try:
            from python_code.ui.contract_format_ar import build_arabic_contract_preview_html
        except ImportError:  # pragma: no cover - direct script fallback
            from ui.contract_format_ar import build_arabic_contract_preview_html

        return build_arabic_contract_preview_html(contract_data)
    if mode == "both":
        return _build_bilingual_contract_preview_html(contract_data)
    return _build_english_contract_preview_html(contract_data)


def create_contract_preview_window(contract_data=None, language=None):
    detected_mode = _detect_contract_language(language=language, contract_data=contract_data)
    if detected_mode == "arabic":
        try:
            from python_code.ui.contract_format_ar import create_arabic_contract_preview_window
        except ImportError:  # pragma: no cover - direct script fallback
            from ui.contract_format_ar import create_arabic_contract_preview_window

        return create_arabic_contract_preview_window(contract_data)
    if detected_mode == "both":
        import urllib.parse

        html_doc = _build_bilingual_contract_preview_html(contract_data)
        webbrowser.open(f"data:text/html;charset=utf-8,{urllib.parse.quote(html_doc)}")
        return None

    root = tk.Tk()
    root.title("Shop Reservation Contract - Starco Commercial Complex")
    root.geometry("1024x860")
    root.minsize(820, 680)

    canvas = tk.Canvas(root)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    content_frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=content_frame, anchor="nw")

    def _on_content_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        if canvas.bbox("all")[3] <= canvas.winfo_height():
            scrollbar.pack_forget()
        else:
            scrollbar.pack(side="right", fill="y")

    content_frame.bind("<Configure>", _on_content_configure)

    def _on_mouse_wheel(event):
        if canvas.bbox("all")[3] > canvas.winfo_height():
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_touchpad_scroll(event):
        if canvas.bbox("all")[3] > canvas.winfo_height():
            canvas.yview_scroll(int(-1 * event.delta), "units")

    canvas.bind_all("<MouseWheel>", _on_mouse_wheel)
    canvas.bind_all("<Shift-MouseWheel>", _on_mouse_wheel)
    canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units") if canvas.bbox("all")[3] > canvas.winfo_height() else None)
    canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units") if canvas.bbox("all")[3] > canvas.winfo_height() else None)
    root.bind("<MouseWheel>", _on_mouse_wheel)
    root.bind("<Shift-MouseWheel>", _on_mouse_wheel)
    root.bind("<Button-4>", lambda event: canvas.yview_scroll(-1, "units") if canvas.bbox("all")[3] > canvas.winfo_height() else None)
    root.bind("<Button-5>", lambda event: canvas.yview_scroll(1, "units") if canvas.bbox("all")[3] > canvas.winfo_height() else None)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    logo_frame = ttk.Frame(content_frame)
    logo_frame.pack(pady=10)

    logo_path = _resolve_logo_path()
    if logo_path and logo_path.exists():
        logo_img = Image.open(logo_path)
        logo_img = logo_img.resize((260, 260), Image.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_img)
        logo_label = tk.Label(logo_frame, image=logo_photo)
        logo_label.pack()
        logo_frame.logo_photo = logo_photo

    title = tk.Label(content_frame, text="STARCO COMMERCIAL COMPLEX", font=("Arial", 22, "bold"), justify="center")
    title.pack(pady=5)

    subtitle = tk.Label(content_frame, text="Shop Reservation Contract", font=("Arial", 18, "bold"))
    subtitle.pack(pady=5)

    payload = _normalize_contract_data(contract_data)
    date_frame = ttk.Frame(content_frame)
    date_frame.pack(fill="x", padx=20, pady=10)
    ttk.Label(date_frame, text=f"Date: {payload['date'] or '__________'}", font=("Arial", 14)).pack(anchor="w")

    parties_frame = ttk.Frame(content_frame)
    parties_frame.pack(fill="x", padx=20, pady=10)
    ttk.Label(parties_frame, text=f"First Party (Lessor): {payload['lessor'] or '__________'}", font=("Arial", 14)).pack(anchor="w")
    ttk.Label(parties_frame, text=f"Second Party (Lessee): {payload['lessee'] or '__________'}", font=("Arial", 14)).pack(anchor="w")
    ttk.Label(parties_frame, text=f"Shop Numbers: {payload['shop_numbers']}", font=("Arial", 14)).pack(anchor="w")
    ttk.Label(parties_frame, text=f"Electricity Account Numbers: {payload['electricity_numbers']}", font=("Arial", 14)).pack(anchor="w")

    rent_frame = ttk.Frame(content_frame)
    rent_frame.pack(fill="x", padx=20, pady=10)
    rent_text = (
        f"It has been agreed between both parties to reserve the above-mentioned shops for the above-mentioned lessee "
        f"for a monthly rent amount of {payload['rent'] or '...........'} OMR for the shops, according to the following conditions:"
    )
    ttk.Label(rent_frame, text=rent_text, font=("Arial", 14), wraplength=850, justify="left").pack(anchor="w")

    conditions_frame = ttk.Frame(content_frame)
    conditions_frame.pack(fill="both", expand=True, padx=20, pady=10)
    conditions_box = tk.Text(conditions_frame, font=("Arial", 14), height=20, wrap="word", padx=10, pady=10)
    conditions_box.pack(fill="both", expand=True)
    conditions_box.insert("1.0", payload["conditions"])
    conditions_box.config(state="disabled")

    sign_frame = ttk.Frame(content_frame)
    sign_frame.pack(fill="x", padx=20, pady=(18, 10))
    ttk.Label(sign_frame, text="Signature of First Party (Lessor):", font=("Arial", 14)).pack(anchor="w", pady=(0, 18))
    ttk.Label(sign_frame, text="Signature & Stamp of Second Party (Lessee):", font=("Arial", 14)).pack(anchor="w")

    deposit_frame = ttk.Frame(content_frame)
    deposit_frame.pack(fill="x", padx=20, pady=10)
    ttk.Label(deposit_frame, text=f"Security Deposit Received: {payload['deposit'] or '__________'} OMR", font=("Arial", 14)).pack(anchor="w")

    bank_frame = ttk.Frame(content_frame)
    bank_frame.pack(fill="x", padx=20, pady=(16, 10))
    ttk.Label(
        bank_frame,
        text=(
            "For bank transfer:\n"
            f"Bank Dhofar – Account Number: {payload['account_number'] or '01041108028002'}\n"
            "Or via mobile name: KHALID9770@BDAF\n"
            f"Account Name: {payload['account_holder'] or 'Khalid Salem Said Al-Shanfari'}"
        ),
        font=("Arial", 12),
        justify="left",
        wraplength=850,
    ).pack(anchor="w")

    root.bind("<Configure>", lambda event: canvas.configure(width=max(700, root.winfo_width() - 35)))
    root.after(50, lambda: canvas.configure(scrollregion=canvas.bbox("all")))
    root.mainloop()


if __name__ == "__main__":
    create_contract_preview_window()
