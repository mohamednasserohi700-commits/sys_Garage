from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import Vehicle, VehicleStatusEnum, Part, StockBalance, PurchaseInvoice, \
    PurchaseInvoiceItem, WorkOrderPart, StockMovement

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../../templates/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    total_cars = Vehicle.query.count()
    finished_cars = Vehicle.query.filter(
        Vehicle.status.in_([VehicleStatusEnum.FINISHED, VehicleStatusEnum.DELIVERED])
    ).count()
    under_maintenance = Vehicle.query.filter_by(status=VehicleStatusEnum.IN_PROGRESS).count()

    # قيمة المخزون = مجموع (رصيد كل قطعة * سعر الشراء)
    stock_value = 0
    for bal in StockBalance.query.all():
        stock_value += bal.quantity * float(bal.part.purchase_price or 0)

    # إجمالي المبيعات = قيمة بيع قطع الغيار المركبة على السيارات
    total_sales = sum(
        (wop.quantity * float(wop.unit_price) for wop in WorkOrderPart.query.all()), 0
    )

    # إجمالي المشتريات
    total_purchases = 0
    for inv in PurchaseInvoice.query.all():
        total_purchases += inv.total

    low_stock_parts = [p for p in Part.query.filter_by(is_active=True).all() if p.is_low_stock]

    recent_vehicles = Vehicle.query.order_by(Vehicle.created_at.desc()).limit(5).all()
    recent_movements = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(8).all()

    return render_template(
        "dashboard/index.html",
        total_cars=total_cars,
        finished_cars=finished_cars,
        under_maintenance=under_maintenance,
        stock_value=stock_value,
        total_sales=total_sales,
        total_purchases=total_purchases,
        low_stock_parts=low_stock_parts,
        recent_vehicles=recent_vehicles,
        recent_movements=recent_movements,
    )
