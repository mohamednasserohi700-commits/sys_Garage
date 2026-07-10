from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import PurchaseInvoice, PurchaseInvoiceItem, Supplier, Warehouse, Part, CompanySettings
from app.services import stock_service
from app.services.numbering import generate_doc_no

purchases_bp = Blueprint("purchases", __name__, template_folder="../../templates/purchases")


@purchases_bp.route("/")
@login_required
def list_purchases():
    invoices = PurchaseInvoice.query.order_by(PurchaseInvoice.invoice_date.desc()).all()
    return render_template("purchases/list.html", invoices=invoices)


@purchases_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_purchase():
    suppliers = Supplier.query.filter_by(is_active=True).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    parts = Part.query.filter_by(is_active=True).all()

    if request.method == "POST":
        try:
            settings = CompanySettings.query.first()
            invoice_no = generate_doc_no(settings.invoice_prefix if settings else "INV-",
                                          settings.next_invoice_no if settings else 1)
            if settings:
                settings.next_invoice_no += 1

            inv = PurchaseInvoice(
                invoice_no=invoice_no,
                supplier_id=int(request.form["supplier_id"]),
                warehouse_id=int(request.form["warehouse_id"]),
                discount=float(request.form.get("discount") or 0),
                tax_percent=float(request.form.get("tax_percent") or 15),
                notes=request.form.get("notes", "").strip(),
                created_by_id=current_user.id,
            )
            db.session.add(inv)
            db.session.flush()

            part_ids = request.form.getlist("part_id[]")
            quantities = request.form.getlist("quantity[]")
            prices = request.form.getlist("unit_price[]")

            if not part_ids:
                raise ValueError("يجب إضافة قطعة واحدة على الأقل للفاتورة")

            for pid, qty, price in zip(part_ids, quantities, prices):
                if not pid or not qty:
                    continue
                qty = int(qty)
                price = float(price)
                item = PurchaseInvoiceItem(invoice_id=inv.id, part_id=int(pid),
                                            quantity=qty, unit_price=price)
                db.session.add(item)
                # زيادة رصيد المخزن تلقائياً
                stock_service.receive_stock(
                    part_id=int(pid), warehouse_id=inv.warehouse_id, quantity=qty,
                    movement_type="in_purchase", reference_no=inv.invoice_no,
                    user_id=current_user.id,
                )
                # تحديث سعر الشراء الأخير للقطعة
                part = Part.query.get(int(pid))
                if part:
                    part.purchase_price = price

            db.session.commit()
            flash(f"تم حفظ فاتورة الشراء {inv.invoice_no} وتحديث المخزون بنجاح", "success")
            return redirect(url_for("purchases.view_purchase", invoice_id=inv.id))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")
    return render_template("purchases/form.html", suppliers=suppliers, warehouses=warehouses, parts=parts)


@purchases_bp.route("/<int:invoice_id>")
@login_required
def view_purchase(invoice_id):
    inv = PurchaseInvoice.query.get_or_404(invoice_id)
    return render_template("purchases/view.html", invoice=inv)
