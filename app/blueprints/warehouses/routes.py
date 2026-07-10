from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from app.extensions import db
from app.models import Warehouse, StockMovement, Part

warehouses_bp = Blueprint("warehouses", __name__, template_folder="../../templates/warehouses")


@warehouses_bp.route("/")
@login_required
def list_warehouses():
    q = request.args.get("q", "").strip()
    query = Warehouse.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Warehouse.name.like(like), Warehouse.code.like(like)))
    warehouses = query.order_by(Warehouse.name).all()
    return render_template("warehouses/list.html", warehouses=warehouses, q=q)


@warehouses_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_warehouse():
    if request.method == "POST":
        try:
            w = Warehouse(
                code=request.form["code"].strip(),
                name=request.form["name"].strip(),
                manager_name=request.form.get("manager_name", "").strip(),
                address=request.form.get("address", "").strip(),
            )
            if not w.code or not w.name:
                raise ValueError("الكود والاسم مطلوبان")
            db.session.add(w)
            db.session.commit()
            flash("تم إضافة المخزن بنجاح", "success")
            return redirect(url_for("warehouses.list_warehouses"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")
    return render_template("warehouses/form.html", warehouse=None)


@warehouses_bp.route("/<int:wid>/edit", methods=["GET", "POST"])
@login_required
def edit_warehouse(wid):
    w = Warehouse.query.get_or_404(wid)
    if request.method == "POST":
        w.name = request.form["name"].strip()
        w.manager_name = request.form.get("manager_name", "").strip()
        w.address = request.form.get("address", "").strip()
        w.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        flash("تم تحديث بيانات المخزن", "success")
        return redirect(url_for("warehouses.list_warehouses"))
    return render_template("warehouses/form.html", warehouse=w)


@warehouses_bp.route("/<int:wid>/delete", methods=["POST"])
@login_required
def delete_warehouse(wid):
    w = Warehouse.query.get_or_404(wid)
    try:
        db.session.delete(w)
        db.session.commit()
        flash("تم حذف المخزن", "success")
    except Exception:
        db.session.rollback()
        flash("لا يمكن حذف هذا المخزن لوجود بيانات مرتبطة به، يمكنك إيقافه بدلاً من ذلك", "danger")
    return redirect(url_for("warehouses.list_warehouses"))


@warehouses_bp.route("/<int:wid>/movements")
@login_required
def warehouse_movements(wid):
    """تقرير الوارد والمنصرف لمخزن معين مع فلاتر"""
    w = Warehouse.query.get_or_404(wid)
    part_id = request.args.get("part_id", type=int)
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    query = StockMovement.query.filter_by(warehouse_id=wid)
    if part_id:
        query = query.filter_by(part_id=part_id)
    if date_from:
        query = query.filter(StockMovement.created_at >= date_from)
    if date_to:
        query = query.filter(StockMovement.created_at <= date_to + " 23:59:59")

    movements = query.order_by(StockMovement.created_at.desc()).all()
    total_in = sum((m.quantity for m in movements if m.quantity > 0), 0)
    total_out = sum((-m.quantity for m in movements if m.quantity < 0), 0)
    parts = Part.query.order_by(Part.name).all()

    return render_template("warehouses/movements.html", warehouse=w, movements=movements,
                            total_in=total_in, total_out=total_out, parts=parts,
                            part_id=part_id, date_from=date_from, date_to=date_to)
