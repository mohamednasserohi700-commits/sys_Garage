from datetime import datetime
from app.extensions import db


class License(db.Model):
    """نظام التفعيل: مفتاح مرتبط باسم الشركة وبصمة الجهاز (ترخيص هذا التثبيت)"""
    __tablename__ = "licenses"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    activation_key = db.Column(db.String(255), unique=True, nullable=False)
    machine_fingerprint = db.Column(db.String(255))    # بصمة الجهاز المرتبط بها المفتاح
    plan = db.Column(db.String(20), default="year")     # "6months" أو "year"
    activated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    @property
    def days_remaining(self):
        return (self.expires_at - datetime.utcnow()).days


class IssuedSerial(db.Model):
    """سجل السريالات (مفاتيح التفعيل) الصادرة للعملاء - يديره الحساب الخفي (administrator) فقط"""
    __tablename__ = "issued_serials"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    machine_fingerprint = db.Column(db.String(255), nullable=False)
    plan = db.Column(db.String(20), nullable=False)
    activation_key = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.String(250))
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
