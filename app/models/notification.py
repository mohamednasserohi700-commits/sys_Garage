from datetime import datetime
from app.extensions import db


class NotificationType:
    DELIVERY_DUE = "delivery_due"       # اقتراب/حلول موعد تسليم سيارة
    LOW_STOCK = "low_stock"             # نقص قطع غيار عن الحد الأدنى
    SYSTEM_ERROR = "system_error"       # خطأ غير متوقع في النظام

    LABELS_AR = {
        DELIVERY_DUE: "موعد تسليم",
        LOW_STOCK: "نقص مخزون",
        SYSTEM_ERROR: "خطأ نظام",
    }
    ICONS = {
        DELIVERY_DUE: "🚗",
        LOW_STOCK: "🔩",
        SYSTEM_ERROR: "⚠️",
    }


class Notification(db.Model):
    """إشعارات ذكية: مواعيد تسليم السيارات، نقص المخزون، وأخطاء النظام"""
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(30), nullable=False, index=True)
    severity = db.Column(db.String(20), default="info")   # info / warning / danger

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    link_url = db.Column(db.String(255))

    related_type = db.Column(db.String(30))    # 'vehicle' / 'part'
    related_id = db.Column(db.Integer)

    # مفتاح فريد لمنع تكرار نفس الإشعار لنفس السبب (مثال: delivery:12 أو lowstock:5)
    dedupe_key = db.Column(db.String(150), unique=True, index=True)
    occurrence_count = db.Column(db.Integer, default=1)

    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def icon(self):
        return NotificationType.ICONS.get(self.type, "🔔")

    @property
    def type_label(self):
        return NotificationType.LABELS_AR.get(self.type, self.type)
