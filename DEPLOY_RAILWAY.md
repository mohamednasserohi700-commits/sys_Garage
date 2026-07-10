# النشر على Railway

## الملفات المضافة خصيصًا للنشر
- **Procfile** / **railway.json** — أمر التشغيل: `python seed.py && gunicorn run:app ...`
- **.python-version** — يحدد Python 3.12
- **requirements.txt** — أضيف له `gunicorn` و`psycopg2-binary` (لدعم PostgreSQL)
- **.gitignore**

## الخطوات

### 1) أنشئ مستودع Git ثم ادفعه (أو استخدم Railway CLI مباشرة)
```bash
cd garage_system
git init
git add .
git commit -m "أول نسخة من نظام مركز الصيانة"
```
ثم ادفعه إلى GitHub وأنشئ مشروع جديد في Railway واربطه بالمستودع.

**أو** بدون Git، باستخدام Railway CLI مباشرة من مجلد المشروع:
```bash
npm i -g @railway/cli
railway login
railway init
railway up
```

### 2) أضف قاعدة بيانات PostgreSQL (مهم جدًا)
من لوحة Railway: **New → Database → Add PostgreSQL**

⚠️ **مهم**: لا تعتمد على SQLite على Railway، لأن نظام الملفات فيه غير دائم (Ephemeral) وستُفقد جميع بياناتك عند كل نشر جديد. بمجرد إضافة PostgreSQL، سيقوم Railway تلقائيًا بحقن متغير `DATABASE_URL` في تطبيقك، والكود يتعرف عليه تلقائيًا (تم تعديل `config.py` ليقرأه ويحوّله للصيغة الصحيحة).

### 3) اضبط متغيرات البيئة (Variables) في مشروع الـ Web Service
| المتغير | القيمة المقترحة |
|---|---|
| `SECRET_KEY` | نص عشوائي طويل وسري (لتشفير الجلسات) |
| `LICENSE_SECRET_KEY` | نص عشوائي طويل وسري آخر (لتوقيع مفاتيح التفعيل) |

`DATABASE_URL` و`PORT` يضبطهما Railway تلقائيًا، لا داعي لإضافتهما يدويًا.

### 4) انشر (Deploy)
Railway سيكتشف المشروع تلقائيًا (Nixpacks + Procfile) وسينفّذ:
```
python seed.py && gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```
`seed.py` آمن للتشغيل المتكرر (Idempotent) — يتحقق قبل كل إضافة، فلن يكرر البيانات عند كل نشر جديد.

### 5) افتح الرابط الذي يولّده Railway
ستجد رابطًا تلقائيًا مثل `https://your-app.up.railway.app`. سجّل دخول بـ:
- اسم المستخدم: `admin`
- كلمة المرور: `admin123`

**غيّر كلمة مرور المدير فورًا من شاشة الإعدادات بعد أول دخول.**

## ملاحظات مهمة بعد النشر
- **الملفات المرفوعة** (شعار الشركة، صور القطع): تُحفظ حاليًا على القرص المحلي للحاوية، وستُفقد عند كل إعادة نشر. إذا احتجت تخزينًا دائمًا للصور، استخدم لاحقًا خدمة تخزين خارجية (مثل Cloudinary أو AWS S3) بدلاً من `UPLOAD_FOLDER` المحلي.
- **النسخ الاحتياطي/الاستعادة** من شاشة الإعدادات مبني حاليًا لـ SQLite فقط. مع PostgreSQL على Railway، استخدم أدوات Railway نفسها للنسخ الاحتياطي (Railway يوفر نسخًا احتياطيًا تلقائيًا لقواعد PostgreSQL من لوحة التحكم)، أو `pg_dump` يدويًا.
- **HTTPS**: Railway يوفره تلقائيًا، لا حاجة لإعداد إضافي.
