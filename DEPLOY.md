# دليل النشر - نظام تسجيل الحضور

## لماذا لا يعمل على GitHub Pages؟

GitHub Pages هو خدمة **static hosting** فقط - أي أنه يعرض ملفات HTML و CSS و JavaScript فقط. 

**المشكلة:**
- Flask يحتاج Python server لتشغيله
- Jinja2 templates تحتاج Flask لتنفيذها
- قاعدة البيانات SQLite تحتاج Python للوصول إليها
- GitHub Pages لا يدعم Python أو أي server-side code

**الحل:**
استخدم خدمة استضافة تدعم Python/Flask مثل:
- ✅ **Render.com** (موصى به - مجاني)
- ✅ **Railway.app** (مجاني)
- ✅ **Heroku** (مدفوع)
- ✅ **Vercel** (يدعم Flask مع إعدادات خاصة)

---

## النشر على Render.com (الطريقة الأسهل)

### الخطوة 1: إعداد المستودع
1. ارفع الكود على GitHub
2. تأكد من وجود جميع الملفات:
   - `requirements.txt`
   - `Procfile`
   - `run.py`
   - `render.yaml` (اختياري)

### الخطوة 2: إنشاء حساب على Render
1. اذهب إلى [render.com](https://render.com)
2. سجل حساب جديد (يمكنك استخدام GitHub)
3. اضغط "New +" → "Web Service"

### الخطوة 3: ربط المستودع
1. اختر "Connect GitHub"
2. اختر المستودع الخاص بك
3. اختر الفرع (Branch) - عادة `main` أو `master`

### الخطوة 4: إعدادات النشر
استخدم الإعدادات التالية:

- **Name:** `attendance-system` (أو أي اسم تريده)
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn run:app`
- **Plan:** Free (مجاني)

### الخطوة 5: النشر
1. اضغط "Create Web Service"
2. انتظر حتى ينتهي البناء (Build) - قد يستغرق 5-10 دقائق
3. بعد النجاح، ستحصل على رابط مثل: `https://attendance-system.onrender.com`

### الخطوة 6: إعداد قاعدة البيانات
- Render سينشئ قاعدة بيانات SQLite جديدة تلقائياً
- البيانات ستُحفظ على الخادم

---

## النشر على Railway.app

### الخطوة 1: إنشاء حساب
1. اذهب إلى [railway.app](https://railway.app)
2. سجل حساب جديد

### الخطوة 2: إنشاء مشروع جديد
1. اضغط "New Project"
2. اختر "Deploy from GitHub repo"
3. اختر المستودع الخاص بك

### الخطوة 3: الإعدادات
- Railway سيكتشف التطبيق تلقائياً
- تأكد من وجود `Procfile` في المستودع

### الخطوة 4: الحصول على الرابط
- بعد النشر، ستحصل على رابط مثل: `https://your-app.railway.app`

---

## ملاحظات مهمة

### 1. قاعدة البيانات
- على Render/Railway، قاعدة البيانات SQLite ستُحفظ على الخادم
- البيانات قد تُفقد عند إعادة النشر (إلا إذا استخدمت قاعدة بيانات خارجية)

### 2. الملفات الثابتة
- تأكد من رفع مجلد `webapp/static/` مع الكود
- CSS و JavaScript سيعملان بشكل طبيعي

### 3. المتغيرات البيئية
- يمكنك إضافة متغيرات بيئية في إعدادات Render/Railway
- مثل: `SECRET_KEY`, `FLASK_ENV=production`

### 4. التحديثات
- عند رفع تحديثات على GitHub، Render/Railway سيعيد النشر تلقائياً
- أو يمكنك النشر يدوياً من لوحة التحكم

---

## استكشاف الأخطاء

### المشكلة: التطبيق لا يعمل
- تحقق من الـ logs في Render/Railway
- تأكد من أن `requirements.txt` يحتوي على جميع الحزم
- تأكد من أن `Start Command` صحيح: `gunicorn run:app`

### المشكلة: قاعدة البيانات فارغة
- هذا طبيعي - قاعدة البيانات جديدة
- أضف بيانات من واجهة التطبيق

### المشكلة: الأخطاء 500
- تحقق من الـ logs
- تأكد من أن جميع الحزم مثبتة بشكل صحيح

---

## روابط مفيدة

- [Render.com Documentation](https://render.com/docs)
- [Railway.app Documentation](https://docs.railway.app)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/latest/deploying/)

---

**ملاحظة:** GitHub Pages مناسب فقط للمواقع الثابتة (HTML/CSS/JS). للتطبيقات الديناميكية مثل Flask، استخدم Render أو Railway.

