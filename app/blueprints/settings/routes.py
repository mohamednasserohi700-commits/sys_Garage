import os
import shutil
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models import CompanySettings
from app.services.license_service import get_machine_fingerprint

settings_bp = Blueprint("settings", __name__, template_folder="../../templates/settings")


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def company_settings():
    s = CompanySettings.query.first()
    if not s:
        s = CompanySettings()
        db.session.add(s)
        db.session.commit()

    if request.method == "POST":
        s.company_name = request.form.get("company_name", "").strip()
        s.phone = request.form.get("phone", "").strip()
        s.address = request.form.get("address", "").strip()
        s.email = request.form.get("email", "").strip()
        s.commercial_register = request.form.get("commercial_register", "").strip()
        s.tax_no = request.form.get("tax_no", "").strip()
        s.tax_percent_default = float(request.form.get("tax_percent_default") or 15)
        s.invoice_prefix = request.form.get("invoice_prefix", "INV-").strip()
        s.workorder_prefix = request.form.get("workorder_prefix", "WO-").strip()

        logo = request.files.get("logo")
        if logo and logo.filename:
            filename = f"logo_{datetime.utcnow().timestamp():.0f}_{logo.filename}"
            path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            logo.save(path)
            s.logo_path = f"uploads/{filename}"

        db.session.commit()
        flash("تم حفظ إعدادات الشركة بنجاح", "success")
        return redirect(url_for("settings.company_settings"))

    return render_template("settings/company.html", settings=s, machine_fingerprint=get_machine_fingerprint())


@settings_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old = request.form.get("old_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if not current_user.check_password(old):
            flash("كلمة المرور الحالية غير صحيحة", "danger")
        elif len(new) < 4:
            flash("كلمة المرور الجديدة يجب ألا تقل عن 4 أحرف", "danger")
        elif new != confirm:
            flash("كلمة المرور الجديدة وتأكيدها غير متطابقين", "danger")
        else:
            current_user.set_password(new)
            db.session.commit()
            flash("تم تغيير كلمة المرور بنجاح", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("settings/change_password.html")


@settings_bp.route("/backup")
@login_required
def backup_database():
    """نسخ احتياطي لقاعدة البيانات (SQLite) للتحميل"""
    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if not db_uri.startswith("sqlite"):
        flash("ميزة النسخ الاحتياطي المباشر متاحة حاليًا فقط مع SQLite، استخدم أدوات SQL Server Backup لقواعد SQL Server", "warning")
        return redirect(url_for("settings.company_settings"))

    db_path = db_uri.replace("sqlite:///", "")
    backup_name = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    backup_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "..", "..", backup_name)
    shutil.copy(db_path, backup_path)
    return send_file(backup_path, as_attachment=True, download_name=backup_name)


@settings_bp.route("/restore", methods=["POST"])
@login_required
def restore_database():
    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if not db_uri.startswith("sqlite"):
        flash("الاستعادة المباشرة متاحة فقط مع SQLite", "warning")
        return redirect(url_for("settings.company_settings"))

    file = request.files.get("backup_file")
    if not file:
        flash("الرجاء اختيار ملف النسخة الاحتياطية", "danger")
        return redirect(url_for("settings.company_settings"))

    db_path = db_uri.replace("sqlite:///", "")
    file.save(db_path)
    flash("تم استعادة قاعدة البيانات بنجاح، يرجى إعادة تشغيل النظام", "success")
    return redirect(url_for("settings.company_settings"))
