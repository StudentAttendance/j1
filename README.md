# نظام تسجيل الحضور

نظام إدارة الحضور للطلبة مبني على Flask.

## المتطلبات

- Python 3.10+
- تثبيت الحزم:
```bash
pip install -r requirements.txt
```

## التشغيل المحلي

```bash
python run.py
```

ثم افتح المتصفح على: `http://localhost:5000`

## النشر على الإنترنت

### خيار 1: استخدام Render.com (موصى به)

1. أنشئ حساب على [Render.com](https://render.com)
2. اضغط على "New +" ثم "Web Service"
3. اربط مستودع GitHub الخاص بك
4. استخدم الإعدادات التالية:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn run:app`
   - **Environment:** Python 3
5. اضغط "Create Web Service"

### خيار 2: استخدام Railway.app

1. أنشئ حساب على [Railway.app](https://railway.app)
2. اضغط "New Project" ثم "Deploy from GitHub repo"
3. اختر المستودع الخاص بك
4. Railway سيكتشف التطبيق تلقائياً

### خيار 3: استخدام Vercel (للتطبيقات الثابتة فقط)

⚠️ **ملاحظة:** Vercel و GitHub Pages لا يدعمان Flask بشكل كامل. استخدم Render أو Railway للتطبيقات الديناميكية.

## الميزات

- ✅ تسجيل الطلبة
- ✅ تسجيل الحضور
- ✅ البحث عن الطلبة
- ✅ إدارة الطلبة (تحديث/حذف)
- ✅ استيراد من Excel
- ✅ تصدير التقارير (Excel/PDF)
- ✅ فلترة حسب المرحلة، الشعبة، المختبر، والمادة

## الملفات

- `run.py` - نقطة البداية للتطبيق
- `webapp/` - مجلد التطبيق الرئيسي
  - `routes.py` - المسارات والوظائف
  - `db.py` - عمليات قاعدة البيانات
  - `templates/` - قوالب HTML
  - `static/` - الملفات الثابتة (CSS)

## قاعدة البيانات

يستخدم التطبيق SQLite محلياً. قاعدة البيانات تُنشأ تلقائياً عند أول تشغيل.

## الترخيص

© 2025 نظام الحضور

