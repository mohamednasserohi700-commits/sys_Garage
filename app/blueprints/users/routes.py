from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, Role, Permission, RolePermission

users_bp = Blueprint("users", __name__, template_folder="../../templates/users")


@users_bp.route("/")
@login_required
def list_users():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(is_hidden=False)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.full_name.like(like), User.username.like(like)))
    users = query.order_by(User.full_name).all()
    return render_template("users/list.html", users=users, q=q)


@users_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_user():
    roles = Role.query.all()
    if request.method == "POST":
        try:
            if User.query.filter_by(username=request.form["username"].strip()).first():
                raise ValueError("اسم المستخدم موجود مسبقًا")
            u = User(
                full_name=request.form["full_name"].strip(),
                username=request.form["username"].strip(),
                phone=request.form.get("phone", "").strip(),
                email=request.form.get("email", "").strip(),
                role_id=int(request.form["role_id"]),
            )
            password = request.form.get("password", "")
            if len(password) < 4:
                raise ValueError("كلمة المرور يجب ألا تقل عن 4 أحرف")
            u.set_password(password)   # تشفير كلمة المرور
            db.session.add(u)
            db.session.commit()
            flash("تم إضافة المستخدم بنجاح", "success")
            return redirect(url_for("users.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")
    return render_template("users/form.html", user=None, roles=roles)


@users_bp.route("/<int:uid>/edit", methods=["GET", "POST"])
@login_required
def edit_user(uid):
    u = User.query.get_or_404(uid)
    if u.is_hidden and not current_user.is_super_admin:
        abort(404)
    roles = Role.query.all()
    if request.method == "POST":
        try:
            u.full_name = request.form["full_name"].strip()
            u.phone = request.form.get("phone", "").strip()
            u.email = request.form.get("email", "").strip()
            u.role_id = int(request.form["role_id"])
            u.is_active_user = bool(request.form.get("is_active_user"))
            new_password = request.form.get("password", "")
            if new_password:
                if len(new_password) < 4:
                    raise ValueError("كلمة المرور يجب ألا تقل عن 4 أحرف")
                u.set_password(new_password)
            db.session.commit()
            flash("تم تحديث بيانات المستخدم", "success")
            return redirect(url_for("users.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")
    return render_template("users/form.html", user=u, roles=roles)


@users_bp.route("/<int:uid>/delete", methods=["POST"])
@login_required
def delete_user(uid):
    if uid == current_user.id:
        flash("لا يمكنك حذف حسابك الحالي", "danger")
        return redirect(url_for("users.list_users"))
    u = User.query.get_or_404(uid)
    if u.is_hidden and not current_user.is_super_admin:
        abort(404)
    db.session.delete(u)
    db.session.commit()
    flash("تم حذف المستخدم", "success")
    return redirect(url_for("users.list_users"))


# ---------------- الأدوار والصلاحيات ----------------
@users_bp.route("/roles")
@login_required
def list_roles():
    roles = Role.query.all()
    return render_template("users/roles.html", roles=roles)


@users_bp.route("/roles/<int:role_id>/permissions", methods=["GET", "POST"])
@login_required
def role_permissions(role_id):
    role = Role.query.get_or_404(role_id)
    permissions = Permission.query.all()

    if request.method == "POST":
        for perm in permissions:
            rp = RolePermission.query.filter_by(role_id=role.id, permission_id=perm.id).first()
            if not rp:
                rp = RolePermission(role_id=role.id, permission_id=perm.id)
                db.session.add(rp)
            prefix = f"perm_{perm.id}_"
            rp.can_view = bool(request.form.get(prefix + "view"))
            rp.can_add = bool(request.form.get(prefix + "add"))
            rp.can_edit = bool(request.form.get(prefix + "edit"))
            rp.can_delete = bool(request.form.get(prefix + "delete"))
            rp.can_print = bool(request.form.get(prefix + "print"))
            rp.can_export = bool(request.form.get(prefix + "export"))
        db.session.commit()
        flash("تم تحديث صلاحيات الدور بنجاح", "success")
        return redirect(url_for("users.list_roles"))

    existing = {rp.permission_id: rp for rp in role.permissions}
    return render_template("users/role_permissions.html", role=role, permissions=permissions, existing=existing)
