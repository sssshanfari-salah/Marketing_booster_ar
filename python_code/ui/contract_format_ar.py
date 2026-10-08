from __future__ import annotations

import html
import urllib.parse
import webbrowser

try:
    from python_code.ui.contract_format import _normalize_contract_data, _resolve_logo_path
except ImportError:  # pragma: no cover - direct script fallback
    from ui.contract_format import _normalize_contract_data, _resolve_logo_path

ARABIC_CONDITIONS = (
    "• يتحمل الطرف الثاني كامل المسؤولية عن الحصول على جميع الموافقات والتصاريح المطلوبة من "
    "الجهات المختصة لمزاولة نشاطه في محلات الطرف الأول. ولا يتحمل الطرف الأول أي مسؤولية تجاه "
    "الطرف الثاني أو أي طرف ثالث بعد توقيع هذا الاتفاق واستلام مبلغ التأمين، في حال إخفاق الطرف "
    "الثاني في الحصول على الموافقات أو التصاريح المطلوبة.\n\n"
    "• يكون عقد الإيجار البلدي الرسمي لمدة سنة واحدة فقط، قابلة للتجديد.\n\n"
    "• يجب تقديم شيك نقدي يعادل إجمالي إيجار شهر واحد عند توقيع هذا العقد، كتأمين وللبدء في "
    "إجراءات عقد الإيجار البلدي.\n\n"
    "• إذا انسحب المستأجر لأي سبب بعد توقيع هذا العقد، فلا يُرد مبلغ التأمين المدفوع.\n\n"
    "• يقوم المؤجر بتركيب الفاصل بين المحلات بعد اعتماد عقد الإيجار البلدي.\n\n"
    "• إذا التزم المستأجر بالعقد، يُحتفظ بالمبلغ المدفوع كتأمين ويُرد إلى المستأجر عند انتهاء "
    "عقد الإيجار، شريطة إعادة المحل أو المحلات بالحالة نفسها التي استُلِمت بها، ودون أي مستحقات "
    "أو ملاحظات قائمة.\n\n"
    "• يجب تقديم شيكات الإيجار الشهري وشيك التأمين بعد توقيع هذا العقد وقبل توقيع عقد الإيجار "
    "البلدي الرسمي.\n\n"
    "الله ولي التوفيق.\n"
)


def build_arabic_contract_preview_html(contract_data=None):
    payload = _normalize_contract_data(contract_data)
    if not isinstance(contract_data, dict) or not contract_data.get("conditions"):
        payload["conditions"] = ARABIC_CONDITIONS

    logo_path = _resolve_logo_path()
    logo_html = ""
    if logo_path and logo_path.exists():
        logo_url = logo_path.resolve().as_uri()
        logo_html = (
            '<div class="brand-block">'
            '<img src="{logo_url}" alt="شعار ستاركو" class="brand-logo" />'
            '<div class="brand-copy"><div class="brand-arabic">مجمع ستاركو التجاري</div>'
            '<div class="brand-name">STARCO COMMERCIAL COMPLEX</div>'
            '<div class="brand-tag">اتفاقية حجز محلات</div></div>'
            '</div>'
        ).format(logo_url=html.escape(str(logo_url), quote=False))

    rent_text = (
        "اتفق الطرفان على حجز المحلات المذكورة أعلاه للمستأجر المذكور أعلاه، "
        f"مقابل إيجار شهري قدره {payload['rent'] or '...........'} ريال عماني، "
        "وذلك وفقاً للشروط التالية:"
    )
    date_value = payload["date"] or "__________"
    deposit_value = payload["deposit"] or "__________"

    return """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>عقد حجز المحلات التجارية</title>
  <style>
    @page {{ size: A4; margin: 18mm; }}
    body {{
      margin: 0;
      background: #f0f2f5;
      font-family: Tahoma, Arial, sans-serif;
      color: #1d1d1d;
      line-height: 1.8;
      direction: rtl;
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
      direction: ltr;
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
      gap: 4px;
      direction: rtl;
      text-align: center;
      flex: 1;
    }}
    .brand-arabic {{
      font-size: 30px;
      color: #123d69;
      font-weight: bold;
      direction: rtl;
      text-align: center;
      letter-spacing: 0.5px;
      line-height: 1.2;
    }}
    .brand-name {{
      font-size: 22px;
      color: #123d69;
      font-weight: bold;
      direction: ltr;
      text-align: center;
      letter-spacing: 0.5px;
      line-height: 1.2;
    }}
    .brand-tag {{
      font-size: 18px;
      color: #53657b;
      text-align: center;
      font-weight: 600;
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
    .ltr {{
      direction: ltr;
      unicode-bidi: isolate;
      display: inline-block;
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
    <h1>عقد حجز المحلات التجارية</h1>

    <div class="meta"><strong>التاريخ:</strong> <span class="ltr">{date}</span></div>

    <div class="party-block">
      <div><strong>الطرف الأول (المؤجر):</strong> <span dir="auto">{lessor}</span></div>
      <div><strong>الطرف الثاني (المستأجر):</strong> <span dir="auto">{lessee}</span></div>
      <div><strong>أرقام المحلات:</strong> <span class="ltr">{shop_numbers}</span></div>
      <div><strong>أرقام حسابات الكهرباء:</strong> <span class="ltr">{electricity_numbers}</span></div>
    </div>

    <div class="rent-text">{rent_text}</div>

    <div class="conditions-box">{conditions}</div>

    <div class="signature-row">
      <div class="signature-box"><strong>توقيع الطرف الأول (المؤجر):</strong></div>
      <div class="signature-box"><strong>توقيع وختم الطرف الثاني (المستأجر):</strong></div>
    </div>

    <div class="row">
      <div><strong>مبلغ التأمين المستلم:</strong> <span class="ltr">{deposit} ريال عماني</span></div>
    </div>

    <div class="bank-block"><strong>للحوالات البنكية:</strong>
بنك ظفار – رقم الحساب: <span class="ltr">{account_number}</span>
أو عبر اسم المستفيد في خدمة الهاتف النقال: <span class="ltr">KHALID9770@BDAF</span>
اسم صاحب الحساب: <span dir="auto">{account_holder}</span></div>
  </div>
</body>
</html>
""".format(
        logo_html=logo_html,
        date=html.escape(str(date_value), quote=False),
        lessor=html.escape(payload["lessor"] or "__________", quote=False),
        lessee=html.escape(payload["lessee"] or "__________", quote=False),
        shop_numbers=html.escape(payload["shop_numbers"], quote=False),
        electricity_numbers=html.escape(payload["electricity_numbers"], quote=False),
        rent_text=html.escape(rent_text, quote=False),
        conditions=html.escape(str(payload["conditions"]), quote=False),
        deposit=html.escape(str(deposit_value), quote=False),
        account_number=html.escape(payload["account_number"], quote=False),
        account_holder=html.escape(payload["account_holder"], quote=False),
    )


def create_arabic_contract_preview_window(contract_data=None):
    html_doc = build_arabic_contract_preview_html(contract_data)
    webbrowser.open(f"data:text/html;charset=utf-8,{urllib.parse.quote(html_doc)}")
    return None