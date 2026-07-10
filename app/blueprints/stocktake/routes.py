from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import StockTake, StockTakeItem, Warehouse, Part, StockBalance
from app.services import stock_service
from app.services.numbering import generate_doc_no

stocktake_bp = Blueprint("stocktake", __name__, template_folder="../../templates/stocktake")


@stocktake_bp.route("/")
@login_required
def list_stocktakes():
    takes = StockTake.query.order_by(StockTake.take_date.desc()).all()
    return render_template("stocktake/list.html", takes=takes)


@stocktake_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_stocktake():
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    warehouse_id = request.args.get("warehouse_id", type=int)
    parts_with_balance = []
    if warehouse_id:
        balances = StockBalance.query.filter_by(warehouse_id=warehouse_id).all()
        parts_with_balance = [(b.part, b.quantity) for b in balances]

    if request.method == "POST":
        try:
            wid = int(request.form["warehouse_id"])
            take = StockTake(
                take_no=generate_doc_no("ST-", StockTake.query.count() + 1),
                warehouse_id=wid, created_by_id=current_user.id,
            )
            db.session.add(take)
            db.session.flush()

            part_ids = request.form.getlist("part_id[]")
            book_qtys = request.form.getlist("book_quantity[]")
            actual_qtys = request.form.getlist("actual_quantity[]")

            for pid, book, actual in zip(part_ids, book_qtys, actual_qtys):
                if not pid or actual == "":
                    continue
                book_q = int(book)
                actual_q = int(actual)
                db.session.add(StockTakeItem(stocktake_id=take.id, part_id=int(pid),
                                              book_quantity=book_q, actual_quantity=actual_q))
                diff = actual_q - book_q
                if diff != 0:
                    stock_service.adjust_stock(
                        part_id=int(pid), warehouse_id=wid, quantity_diff=diff,
                        reason=f"جرد فعلي رقم {take.take_no}", user_id=current_user.id,
                    )
            db.session.commit()
            flash(f"تم حفظ سند الجرد {take.take_no} وتعديل الأرصدة", "success")
            return redirect(url_for("stocktake.list_stocktakes"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")

    return render_template("stocktake/form.html", warehouses=warehouses,
                            warehouse_id=warehouse_id, parts_with_balance=parts_with_balance)
