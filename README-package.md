# Packaging the app

## 1) Build the executable

From the project root, run:

```bash
python package_app.py
```

This will:
- install PyInstaller if needed
- package the app into a single Windows executable
- create a desktop shortcut on the Windows Desktop

## 2) Desktop shortcut

The script creates a shortcut named:

```text
Marketing Booster AR.lnk
```

## 3) Notes

- The packaged app reads and writes the client data file next to the executable if present.
- If no data file is found, it will create one in the executable folder.

اسم المشروع
معزّز التسويق النسخة العربية
Marketing Booster

الهدف
توفير أدوات ومسارات عمل تساعد في تخطيط وإنشاء وتحسين الحملات التسويقية باستخدام لغة بايثون.

المميزات
تخطيط وتنظيم الحملات التسويقية

دعم إنشاء المحتوى التسويقي

معالجة البيانات وتحليلها

مسارات عمل قابلة للتوسّع مبنية على بايثون

تتبّع تقدّم الحملات التسويقية لكل عميل

طريقة التشغيل
أكمل خطوات الإعداد الموضّحة أدناه.

افتح موجّه الأوامر داخل مجلد المشروع.

شغّل نقطة الدخول المناسبة في بايثون، على سبيل المثال:

bash