"""
خدمة الإشعارات الذكية
----------------------
تولّد إشعارات تلقائية عن:
  1) اقتراب/حلول موعد تسليم سيارة للعميل (delivery_due)
  2) نقص قطع الغيار عن الحد الأدنى (low_stock)
  3) أي خطأ غير متوقع يحدث في النظام (system_error)

تعتمد فكرة "dedupe_key" لمنع تكرار نفس الإشعار كل مرة يتم فيها الفحص،
ويتم حذف الإشعار تلقائيًا لو السبب زال (تم التسليم / اتحل نقص المخزون).
"""
import hashlib
import time
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Notification, NotificationType, Vehicle, VehicleStatusEnum, Part

# عدد الأيام التي يُعتبر بعدها موعد التسليم "قريب"
DUE_SOON_DAYS = 2

# فاصل زمني (بالثواني) بين كل تحديث تلقائي لإشعارات المواعيد والمخزون
_REFRESH_INTERVAL = 60
_last_refresh_ts = 0


def _upsert(dedupe_key, type_, severity, title, message, link_url=None,
            related_type=None, related_id=None):
    existing = Notification.query.filter_by(dedupe_key=dedupe_key).first()
    if existing:
        # حدّث البيانات، وإن ارتفعت الخطورة (مثلاً من تنبيه إلى تأخير) أعده كغير مقروء
        escalated = _severity_rank(severity) > _severity_rank(existing.severity)
        existing.severity = severity
        existing.title = title
        existing.message = message
        existing.link_url = link_url
        existing.updated_at = datetime.utcnow()
        existing.occurrence_count = (existing.occurrence_count or 1) + 1
        if escalated:
            existing.is_read = False
        return existing
    else:
        n = Notification(
            type=type_, severity=severity, title=title, message=message, link_url=link_url,
            related_type=related_type, related_id=related_id, dedupe_key=dedupe_key,
        )
        db.session.add(n)
        return n


def _severity_rank(sev):
    return {"info": 0, "warning": 1, "danger": 2}.get(sev, 0)


def _cleanup_resolved(type_, active_keys):
    """يحذف إشعارات نوع معين لم تعد أسبابها قائمة"""
    stale = Notification.query.filter(
        Notification.type == type_,
        ~Notification.dedupe_key.in_(active_keys) if active_keys else True,
    ).all()
    for n in stale:
        db.session.delete(n)


def _generate_delivery_due_notifications():
    now = datetime.utcnow()
    soon_limit = now + timedelta(days=DUE_SOON_DAYS)

    pending_vehicles = Vehicle.query.filter(
        Vehicle.status != VehicleStatusEnum.DELIVERED,
        Vehicle.expected_delivery_date.isnot(None),
    ).all()

    active_keys = []
    for v in pending_vehicles:
        key = f"delivery:{v.id}"
        if v.expected_delivery_date < now:
            days_late = (now - v.expected_delivery_date).days
            active_keys.append(key)
            _upsert(
                dedupe_key=key, type_=NotificationType.DELIVERY_DUE, severity="danger",
                title=f"تأخر تسليم السيارة {v.plate_no}",
                message=f"السيارة ({v.car_type}) للعميل {v.customer_name} تجاوزت موعد التسليم "
                        f"المتوقع منذ {days_late} يوم/أيام. رقم الأمر: {v.order_no}",
                link_url=f"/vehicles/{v.id}",
                related_type="vehicle", related_id=v.id,
            )
        elif v.expected_delivery_date <= soon_limit:
            hours_left = int((v.expected_delivery_date - now).total_seconds() // 3600)
            active_keys.append(key)
            _upsert(
                dedupe_key=key, type_=NotificationType.DELIVERY_DUE, severity="warning",
                title=f"اقتراب موعد تسليم السيارة {v.plate_no}",
                message=f"السيارة ({v.car_type}) للعميل {v.customer_name} موعد تسليمها خلال "
                        f"{max(hours_left, 0)} ساعة تقريبًا. رقم الأمر: {v.order_no}",
                link_url=f"/vehicles/{v.id}",
                related_type="vehicle", related_id=v.id,
            )

    _cleanup_resolved(NotificationType.DELIVERY_DUE, active_keys)


def _generate_low_stock_notifications():
    parts = Part.query.filter_by(is_active=True).all()
    active_keys = []
    for p in parts:
        if not p.is_low_stock:
            continue
        key = f"lowstock:{p.id}"
        active_keys.append(key)
        balance = p.total_balance
        if balance <= 0:
            severity = "danger"
            title = f"نفاذ قطعة الغيار: {p.name}"
            message = f"القطعة '{p.name}' ({p.code}) نفدت تمامًا من جميع المخازن. يرجى إعادة الطلب."
        else:
            severity = "warning"
            title = f"نقص مخزون: {p.name}"
            message = (f"الرصيد الحالي لقطعة '{p.name}' ({p.code}) هو {balance} "
                       f"وهو أقل من أو يساوي الحد الأدنى ({p.min_quantity}).")
        _upsert(
            dedupe_key=key, type_=NotificationType.LOW_STOCK, severity=severity,
            title=title, message=message, link_url=f"/parts/{p.id}/edit",
            related_type="part", related_id=p.id,
        )
    _cleanup_resolved(NotificationType.LOW_STOCK, active_keys)


def generate_notifications(force=False):
    """يفحص السيارات المتأخرة/القريبة من التسليم وقطع الغيار الناقصة وينشئ/يحدّث الإشعارات.
    يتم تحديد معدل التنفيذ (throttling) لتفادي فحص قاعدة البيانات في كل طلب."""
    global _last_refresh_ts
    now_ts = time.time()
    if not force and (now_ts - _last_refresh_ts) < _REFRESH_INTERVAL:
        return
    _last_refresh_ts = now_ts
    try:
        _generate_delivery_due_notifications()
        _generate_low_stock_notifications()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def log_system_error(error_message: str, details: str = None):
    """يسجل إشعار خطأ نظام. يتم تجميع نفس الخطأ المتكرر خلال ساعة في إشعار واحد بدل تكراره."""
    try:
        digest = hashlib.md5(error_message.encode("utf-8", errors="ignore")).hexdigest()[:16]
        key = f"error:{digest}"
        existing = Notification.query.filter_by(dedupe_key=key).first()
        if existing and existing.updated_at and (datetime.utcnow() - existing.updated_at) < timedelta(hours=1):
            existing.occurrence_count = (existing.occurrence_count or 1) + 1
            existing.updated_at = datetime.utcnow()
            existing.is_read = False
        else:
            n = Notification(
                type=NotificationType.SYSTEM_ERROR, severity="danger",
                title="حدث خطأ غير متوقع في النظام",
                message=(details or error_message)[:490],
                dedupe_key=key,
            )
            db.session.add(n)
        db.session.commit()
    except Exception:
        db.session.rollback()


def get_unread_count():
    return Notification.query.filter_by(is_read=False).count()


def get_recent(limit=8):
    return Notification.query.order_by(Notification.created_at.desc()).limit(limit).all()
