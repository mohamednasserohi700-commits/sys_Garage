from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from app.extensions import db
from app.models import Supplier

suppliers_bp = Blueprint("suppliers", __name__, template_folder="../../templates/suppliers")


@suppliers_bp.route("/")
@login_required
def list_suppliers():
    q = request.args.get("q", "").strip()
    query = Supplier.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Supplier.name.like(like), Supplier.phone.like(like)))
    suppliers = query.order_by(Supplier.name).all()
    return render_template("suppliers/list.html", suppliers=suppliers, q=q)


@suppliers_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_supplier():
    if request.method == "POST":
        try:
            s = Supplier(
                name=request.form["name"].strip(),
                phone=request.form.get("phone", "").strip(),
                email=request.form.get("email", "").strip(),
                address=request.form.get("address", "").strip(),
                tax_no=request.form.get("tax_no", "").strip(),
                notes=request.form.get("notes", "").strip(),
            )
            if not s.name:
                raise ValueError("اسم المورد مطلوب")
            db.session.add(s)
            db.session.commit()
            flash("تم إضافة المورد بنجاح", "success")
            return redirect(url_for("suppliers.list_suppliers"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")
    return render_template("suppliers/form.html", supplier=None)


@suppliers_bp.route("/<int:sid>/edit", methods=["GET", "POST"])
@login_required
def edit_supplier(sid):
    s = Supplier.query.get_or_404(sid)
    if request.method == "POST":
        s.name = request.form["name"].strip()
        s.phone = request.form.get("phone", "").strip()
        s.email = request.form.get("email", "").strip()
        s.address = request.form.get("address", "").strip()
        s.tax_no = request.form.get("tax_no", "").strip()
        s.notes = request.form.get("notes", "").strip()
        s.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        flash("تم تحديث بيانات المورد", "success")
        return redirect(url_for("suppliers.list_suppliers"))
    return render_template("suppliers/form.html", supplier=s)


@suppliers_bp.route("/<int:sid>/delete", methods=["POST"])
@login_required
def delete_supplier(sid):
    s = Supplier.query.get_or_404(sid)
    try:
        db.session.delete(s)
        db.session.commit()
        flash("تم حذف المورد", "success")
    except Exception:
        db.session.rollback()
        flash("لا يمكن حذف هذا المورد لوجود بيانات مرتبطة به", "danger")
    return redirect(url_for("suppliers.list_suppliers"))
