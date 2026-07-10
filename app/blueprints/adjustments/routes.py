from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import StockAdjustment, Warehouse, Part
from app.services import stock_service
from app.services.numbering import generate_doc_no

adjustments_bp = Blueprint("adjustments", __name__, template_folder="../../templates/adjustments")


@adjustments_bp.route("/")
@login_required
def list_adjustments():
    items = StockAdjustment.query.order_by(StockAdjustment.created_at.desc()).all()
    return render_template("adjustments/list.html", items=items)


@adjustments_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_adjustment():
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    parts = Part.query.filter_by(is_active=True).all()
    if request.method == "POST":
        try:
            part_id = int(request.form["part_id"])
            warehouse_id = int(request.form["warehouse_id"])
            qty = int(request.form["quantity"])
            reason = request.form["reason"].strip()
            if not reason:
                raise ValueError("سبب التسوية مطلوب")

            adj = StockAdjustment(
                adjustment_no=generate_doc_no("ADJ-", StockAdjustment.query.count() + 1),
                part_id=part_id, warehouse_id=warehouse_id, quantity=qty,
                reason=reason, user_id=current_user.id,
            )
            db.session.add(adj)
            stock_service.adjust_stock(part_id, warehouse_id, qty, reason, current_user.id)
            db.session.commit()
            flash("تم حفظ سند التسوية بنجاح", "success")
            return redirect(url_for("adjustments.list_adjustments"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")
    return render_template("adjustments/form.html", warehouses=warehouses, parts=parts)
