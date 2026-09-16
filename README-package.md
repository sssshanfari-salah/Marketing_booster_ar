# Packaging the app

## 1) Build the executable

From the project root, run:

```bash
python package_app.py
```

This will:
- install PyInstaller if needed
- package the app into a single Windows executable
- create a desktop shortcut named Clients Manager on the Windows Desktop

## 2) Desktop shortcut

The script creates a shortcut named:

```text
Clients Manager.lnk
```

## 3) Notes

- The packaged app reads and writes the client data file next to the executable if present.
- If no data file is found, it will create one in the executable folder.
- The current app branding is Clients Manager, while the executable build name remains the project’s legacy package name for compatibility.

اسم المشروع
Clients Manager

الهدف
إدارة سجلات العملاء وتفاصيل الاتصال والأعمال وتقدم المهام من خلال تطبيق سطح مكتب بسيط.

المميزات
تسجيل العملاء وإدارة جهات الاتصال

تنسيق أرقام الاتصال حسب الدولة

مراجعات العملاء وتتبع تقدم المهام

تصدير معلومات العميل بصيغة نصية أو vCard

تدفق سطح مكتب بسيط لإدارة العملاء محليًا

طريقة التشغيل
أكمل خطوات الإعداد الموضّحة أدناه.

افتح موجه الأوامر داخل مجلد المشروع.

شغّل نقطة الدخول المناسبة في بايثون، على سبيل المثال:

bash