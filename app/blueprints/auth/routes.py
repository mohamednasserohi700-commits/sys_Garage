from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__, template_folder="../../templates/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        if not username or not password:
            flash("الرجاء إدخال اسم المستخدم وكلمة المرور", "danger")
            return render_template("auth/login.html")

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("اسم المستخدم أو كلمة المرور غير صحيحة", "danger")
            return render_template("auth/login.html")

        if not user.is_active_user:
            flash("تم إيقاف هذا الحساب، يرجى مراجعة المدير", "danger")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح", "success")
    return redirect(url_for("auth.login"))
