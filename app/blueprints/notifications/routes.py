from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required

from app.extensions import db
from app.models import Notification
from app.services import notification_service

notifications_bp = Blueprint("notifications", __name__, template_folder="../../templates/notifications")


@notifications_bp.route("/")
@login_required
def list_notifications():
    notification_service.generate_notifications(force=True)
    filter_type = request.args.get("type", "")
    query = Notification.query
    if filter_type:
        query = query.filter_by(type=filter_type)
    items = query.order_by(Notification.is_read.asc(), Notification.created_at.desc()).all()
    unread_count = notification_service.get_unread_count()
    return render_template("notifications/list.html", items=items, unread_count=unread_count,
                            filter_type=filter_type)


@notifications_bp.route("/recent")
@login_required
def recent_notifications():
    """يُستدعى دوريًا عبر JS لتحديث جرس الإشعارات بدون إعادة تحميل الصفحة"""
    notification_service.generate_notifications()
    items = notification_service.get_recent(limit=8)
    return jsonify({
        "unread_count": notification_service.get_unread_count(),
        "items": [{
            "id": n.id,
            "type": n.type,
            "type_label": n.type_label,
            "icon": n.icon,
            "severity": n.severity,
            "title": n.title,
            "message": n.message,
            "link_url": n.link_url,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M"),
        } for n in items],
    })


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    n = Notification.query.get_or_404(notification_id)
    n.is_read = True
    db.session.commit()
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})
    return redirect(n.link_url or url_for("notifications.list_notifications"))


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})
    return redirect(url_for("notifications.list_notifications"))


@notifications_bp.route("/<int:notification_id>/delete", methods=["POST"])
@login_required
def delete_notification(notification_id):
    n = Notification.query.get_or_404(notification_id)
    db.session.delete(n)
    db.session.commit()
    return redirect(url_for("notifications.list_notifications"))
