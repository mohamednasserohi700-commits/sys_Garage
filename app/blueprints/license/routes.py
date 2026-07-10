from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import License, IssuedSerial
from app.services.license_service import get_machine_fingerprint, verify_activation_key, \
    generate_activation_key, PLAN_DAYS

license_bp = Blueprint("license", __name__, template_folder="../../templates/license")


@license_bp.route("/activate", methods=["GET", "POST"])
def activate():
    fingerprint = get_machine_fingerprint()
    if request.method == "POST":
        key = request.form.get("activation_key", "").strip()
        try:
            data = verify_activation_key(key, fingerprint)
            existing = License.query.first()
            if existing:
                db.session.delete(existing)
            lic = License(
                company_name=data["c"],
                activation_key=key,
                machine_fingerprint=fingerprint,
                plan=data["p"],
                expires_at=datetime.strptime(data["e"], "%Y-%m-%d"),
                is_active=True,
            )
            db.session.add(lic)
            db.session.commit()
            flash("تم تفعيل النظام بنجاح", "success")
            return redirect(url_for("dashboard.index"))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template("license/activate.html", fingerprint=fingerprint)


@license_bp.route("/status")
@login_required
def status():
    # هذه الشاشة مخصصة للحساب الخفي فقط، غير ظاهرة وغير متاحة للمدير العادي أو المستخدمين
    if not current_user.is_super_admin:
        abort(404)
    lic = License.query.first()
    return render_template("license/status.html", lic=lic)


# ---------------- إدارة وإصدار السريالات (حصريًا للحساب الخفي administrator) ----------------
@license_bp.route("/serials", methods=["GET", "POST"])
@login_required
def serials():
    if not current_user.is_super_admin:
        abort(404)   # 404 وليس 403 حتى لا يظهر أي أثر لوجود هذه الشاشة لغير المصرح لهم

    generated_key = None
    if request.method == "POST":
        try:
            company_name = request.form["company_name"].strip()
            machine_fingerprint = request.form["machine_fingerprint"].strip()
            plan = request.form["plan"]
            notes = request.form.get("notes", "").strip()

            if not company_name or not machine_fingerprint:
                raise ValueError("اسم الشركة وبصمة الجهاز مطلوبان")
            if plan not in PLAN_DAYS:
                raise ValueError("خطة اشتراك غير معروفة")

            generated_key = generate_activation_key(company_name, machine_fingerprint, plan)
            data = verify_activation_key(generated_key, machine_fingerprint)

            db.session.add(IssuedSerial(
                company_name=company_name, machine_fingerprint=machine_fingerprint,
                plan=plan, activation_key=generated_key,
                expires_at=datetime.strptime(data["e"], "%Y-%m-%d"), notes=notes,
            ))
            db.session.commit()
            flash("تم إصدار السريال بنجاح، انسخه من الأسفل وأرسله للعميل", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")

    issued = IssuedSerial.query.order_by(IssuedSerial.issued_at.desc()).all()
    return render_template("license/serials.html", issued=issued, generated_key=generated_key)


@license_bp.route("/serials/<int:serial_id>/delete", methods=["POST"])
@login_required
def delete_serial(serial_id):
    if not current_user.is_super_admin:
        abort(404)
    s = IssuedSerial.query.get_or_404(serial_id)
    db.session.delete(s)
    db.session.commit()
    flash("تم حذف السريال من السجل", "success")
    return redirect(url_for("license.serials"))
