from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class Role(db.Model):
    """الأدوار الوظيفية: مدير، فني، محاسب، مستخدم عرض فقط ... إلخ"""
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    users = db.relationship("User", back_populates="role")
    permissions = db.relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role {self.name}>"


class Permission(db.Model):
    """الشاشة/الوحدة التي يمكن التحكم بصلاحياتها (سيارات، مخازن، تقارير ...)"""
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)   # مثال: vehicles
    name_ar = db.Column(db.String(100), nullable=False)            # مثال: إدارة السيارات

    role_links = db.relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(db.Model):
    """الربط بين الدور والشاشة مع تحديد نوع الصلاحية (عرض/إضافة/تعديل/حذف/طباعة/تصدير)"""
    __tablename__ = "role_permissions"

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey("permissions.id"), nullable=False)

    can_view = db.Column(db.Boolean, default=True)
    can_add = db.Column(db.Boolean, default=False)
    can_edit = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)
    can_print = db.Column(db.Boolean, default=False)
    can_export = db.Column(db.Boolean, default=False)

    role = db.relationship("Role", back_populates="permissions")
    permission = db.relationship("Permission", back_populates="role_links")

    __table_args__ = (db.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)


class User(db.Model, UserMixin):
    """المستخدمون"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    is_active_user = db.Column(db.Boolean, default=True)
    is_hidden = db.Column(db.Boolean, default=False)   # مستخدم خفي (لا يظهر في شاشة إدارة المستخدمين)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    role = db.relationship("Role", back_populates="users")

    # -- كلمة المرور --
    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # مطلوبة من Flask-Login
    @property
    def is_active(self):
        return self.is_active_user

    @property
    def is_super_admin(self):
        """الحساب الخفي الخاص بمزود النظام: يملك كل الصلاحيات ويدير التفعيل والسريالات"""
        return self.username == "administrator" and self.is_hidden

    def has_permission(self, code: str, action: str = "view") -> bool:
        """التحقق من صلاحية المستخدم على شاشة معينة وإجراء معين"""
        if self.is_super_admin:
            return True
        if self.role and self.role.name == "Admin":
            return True
        for rp in self.role.permissions:
            if rp.permission.code == code:
                return getattr(rp, f"can_{action}", False)
        return False

    def __repr__(self):
        return f"<User {self.username}>"
