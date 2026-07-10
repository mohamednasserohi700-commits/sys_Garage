from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import StockTransfer, StockTransferItem, Warehouse, Part
from app.services import stock_service
from app.services.numbering import generate_doc_no

transfers_bp = Blueprint("transfers", __name__, template_folder="../../templates/transfers")


@transfers_bp.route("/")
@login_required
def list_transfers():
    transfers = StockTransfer.query.order_by(StockTransfer.transfer_date.desc()).all()
    return render_template("transfers/list.html", transfers=transfers)


@transfers_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_transfer():
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    parts = Part.query.filter_by(is_active=True).all()

    if request.method == "POST":
        try:
            from_wh = int(request.form["from_warehouse_id"])
            to_wh = int(request.form["to_warehouse_id"])
            if from_wh == to_wh:
                raise ValueError("لا يمكن التحويل لنفس المخزن")

            transfer = StockTransfer(
                transfer_no=generate_doc_no("TR-", StockTransfer.query.count() + 1),
                from_warehouse_id=from_wh,
                to_warehouse_id=to_wh,
                notes=request.form.get("notes", "").strip(),
                created_by_id=current_user.id,
                is_approved=True,
            )
            db.session.add(transfer)
            db.session.flush()

            part_ids = request.form.getlist("part_id[]")
            quantities = request.form.getlist("quantity[]")
            if not part_ids:
                raise ValueError("يجب إضافة قطعة واحدة على الأقل")

            for pid, qty in zip(part_ids, quantities):
                if not pid or not qty:
                    continue
                qty = int(qty)
                part = Part.query.get(int(pid))
                db.session.add(StockTransferItem(transfer_id=transfer.id, part_id=int(pid), quantity=qty))
                # خصم من المصدر وإضافة للمستلم (يمنع التحويل عند نقص الرصيد)
                stock_service.transfer_stock(
                    part_id=int(pid), from_warehouse_id=from_wh, to_warehouse_id=to_wh,
                    quantity=qty, reference_no=transfer.transfer_no, user_id=current_user.id,
                    part_name=part.name if part else "",
                )

            db.session.commit()
            flash(f"تم إنشاء واعتماد سند التحويل {transfer.transfer_no}", "success")
            return redirect(url_for("transfers.list_transfers"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")
    return render_template("transfers/form.html", warehouses=warehouses, parts=parts)
