from flask import Blueprint, render_template, request, send_file
from flask_login import login_required

from app.models import Vehicle, VehicleStatusEnum, Part, StockMovement, WorkOrderPart, \
    PurchaseInvoice, Supplier, Warehouse, StockBalance, StockTake, StockAdjustment, CompanySettings
from app.services.export_service import export_to_excel, export_to_pdf

reports_bp = Blueprint("reports", __name__, template_folder="../../templates/reports")

REPORT_LIST = [
    ("current_cars", "السيارات الحالية"),
    ("finished_cars", "السيارات المنتهية"),
    ("under_maintenance_cars", "السيارات تحت الصيانة"),
    ("issued_parts", "قطع الغيار المصروفة"),
    ("current_stock", "المخزون الحالي"),
    ("low_stock", "الأصناف الناقصة"),
    ("dead_stock", "الأصناف الراكدة"),
    ("purchases", "المشتريات"),
    ("profits", "الأرباح"),
    ("stocktakes", "الجرد"),
    ("adjustments", "التسويات"),
]


@reports_bp.route("/")
@login_required
def index():
    return render_template("reports/index.html", reports=REPORT_LIST)


def _company_name():
    s = CompanySettings.query.first()
    return s.company_name if s else "مركز الصيانة"


def _build_report(code):
    """يبني (العنوان، العناوين، الصفوف) لكل نوع تقرير"""
    if code == "current_cars":
        rows = Vehicle.query.order_by(Vehicle.created_at.desc()).all()
        headers = ["رقم الأمر", "العميل", "الهاتف", "نوع السيارة", "اللوحة", "الحالة", "تاريخ الدخول"]
        data = [[v.order_no, v.customer_name, v.customer_phone, v.car_type, v.plate_no,
                 v.status_label, v.entry_date.strftime("%Y-%m-%d") if v.entry_date else ""] for v in rows]
        return "تقرير السيارات الحالية", headers, data

    if code == "finished_cars":
        rows = Vehicle.query.filter(Vehicle.status.in_(
            [VehicleStatusEnum.FINISHED, VehicleStatusEnum.DELIVERED])).all()
        headers = ["رقم الأمر", "العميل", "نوع السيارة", "اللوحة", "تاريخ التسليم"]
        data = [[v.order_no, v.customer_name, v.car_type, v.plate_no,
                 v.actual_delivery_date.strftime("%Y-%m-%d") if v.actual_delivery_date else "-"] for v in rows]
        return "تقرير السيارات المنتهية", headers, data

    if code == "under_maintenance_cars":
        rows = Vehicle.query.filter_by(status=VehicleStatusEnum.IN_PROGRESS).all()
        headers = ["رقم الأمر", "العميل", "نوع السيارة", "اللوحة", "الفني المسؤول", "تاريخ الدخول"]
        data = [[v.order_no, v.customer_name, v.car_type, v.plate_no,
                 v.technician.full_name if v.technician else "-",
                 v.entry_date.strftime("%Y-%m-%d") if v.entry_date else ""] for v in rows]
        return "تقرير السيارات تحت الصيانة", headers, data

    if code == "issued_parts":
        rows = WorkOrderPart.query.order_by(WorkOrderPart.created_at.desc()).all()
        headers = ["أمر الصيانة", "القطعة", "الكمية", "سعر البيع", "الإجمالي", "الفني", "التاريخ"]
        data = [[w.vehicle.order_no, w.part.name, w.quantity, float(w.unit_price), w.total_price,
                 w.technician.full_name if w.technician else "-",
                 w.created_at.strftime("%Y-%m-%d")] for w in rows]
        return "تقرير قطع الغيار المصروفة", headers, data

    if code == "current_stock":
        rows = StockBalance.query.filter(StockBalance.quantity > 0).all()
        headers = ["كود القطعة", "اسم القطعة", "المخزن", "الرصيد", "سعر الشراء", "قيمة الرصيد"]
        data = [[b.part.code, b.part.name, b.warehouse.name, b.quantity,
                 float(b.part.purchase_price), b.quantity * float(b.part.purchase_price)] for b in rows]
        return "تقرير المخزون الحالي", headers, data

    if code == "low_stock":
        parts = [p for p in Part.query.filter_by(is_active=True).all() if p.is_low_stock]
        headers = ["كود القطعة", "اسم القطعة", "الرصيد الحالي", "أقل كمية"]
        data = [[p.code, p.name, p.total_balance, p.min_quantity] for p in parts]
        return "تقرير الأصناف الناقصة", headers, data

    if code == "dead_stock":
        # أصناف لم تتحرك (لا يوجد لها حركة صرف) خلال آخر 90 يوم أو لا يوجد لها حركة إطلاقًا
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=90)
        parts = Part.query.filter_by(is_active=True).all()
        dead = []
        for p in parts:
            last_out = StockMovement.query.filter(
                StockMovement.part_id == p.id, StockMovement.quantity < 0
            ).order_by(StockMovement.created_at.desc()).first()
            if p.total_balance > 0 and (not last_out or last_out.created_at < cutoff):
                dead.append((p, last_out))
        headers = ["كود القطعة", "اسم القطعة", "الرصيد الحالي", "آخر حركة صرف"]
        data = [[p.code, p.name, p.total_balance,
                 lo.created_at.strftime("%Y-%m-%d") if lo else "لا يوجد"] for p, lo in dead]
        return "تقرير الأصناف الراكدة (أكثر من 90 يوم بدون حركة)", headers, data

    if code == "purchases":
        rows = PurchaseInvoice.query.order_by(PurchaseInvoice.invoice_date.desc()).all()
        headers = ["رقم الفاتورة", "المورد", "المخزن", "التاريخ", "الإجمالي"]
        data = [[i.invoice_no, i.supplier.name, i.warehouse.name,
                 i.invoice_date.strftime("%Y-%m-%d"), i.total] for i in rows]
        return "تقرير المشتريات", headers, data

    if code == "profits":
        rows = WorkOrderPart.query.all()
        headers = ["أمر الصيانة", "القطعة", "الكمية", "التكلفة", "البيع", "الربح"]
        data = []
        total_profit = 0
        for w in rows:
            profit = w.total_price - w.total_cost
            total_profit += profit
            data.append([w.vehicle.order_no, w.part.name, w.quantity, w.total_cost, w.total_price, profit])
        data.append(["", "", "", "", "الإجمالي", total_profit])
        return "تقرير الأرباح (من قطع الغيار المصروفة)", headers, data

    if code == "stocktakes":
        rows = StockTake.query.order_by(StockTake.take_date.desc()).all()
        headers = ["رقم الجرد", "المخزن", "التاريخ", "عدد الأصناف"]
        data = [[s.take_no, s.warehouse.name, s.take_date.strftime("%Y-%m-%d"), len(s.items)] for s in rows]
        return "تقرير سندات الجرد", headers, data

    if code == "adjustments":
        rows = StockAdjustment.query.order_by(StockAdjustment.created_at.desc()).all()
        headers = ["رقم السند", "القطعة", "المخزن", "الكمية", "السبب", "التاريخ"]
        data = [[a.adjustment_no, a.part.name, a.warehouse.name, a.quantity, a.reason,
                 a.created_at.strftime("%Y-%m-%d")] for a in rows]
        return "تقرير التسويات", headers, data

    return "تقرير غير معروف", [], []


@reports_bp.route("/vehicle/<int:vehicle_id>")
@login_required
def vehicle_report(vehicle_id):
    v = Vehicle.query.get_or_404(vehicle_id)
    headers = ["القطعة", "الكمية", "سعر البيع", "الإجمالي", "التاريخ", "الفني"]
    data = [[w.part.name, w.quantity, float(w.unit_price), w.total_price,
             w.created_at.strftime("%Y-%m-%d"), w.technician.full_name if w.technician else "-"]
            for w in v.parts_used]
    title = f"تقرير سيارة - أمر الصيانة {v.order_no}"
    return render_template("reports/preview.html", title=title, headers=headers, rows=data,
                            code=f"vehicle_{vehicle_id}")


@reports_bp.route("/supplier/<int:supplier_id>")
@login_required
def supplier_report(supplier_id):
    s = Supplier.query.get_or_404(supplier_id)
    invoices = PurchaseInvoice.query.filter_by(supplier_id=supplier_id).all()
    headers = ["رقم الفاتورة", "التاريخ", "المخزن", "الإجمالي"]
    data = [[i.invoice_no, i.invoice_date.strftime("%Y-%m-%d"), i.warehouse.name, i.total] for i in invoices]
    title = f"تقرير المورد - {s.name}"
    return render_template("reports/preview.html", title=title, headers=headers, rows=data,
                            code=f"supplier_{supplier_id}")


@reports_bp.route("/customer")
@login_required
def customer_report():
    phone = request.args.get("phone", "").strip()
    vehicles = []
    if phone:
        vehicles = Vehicle.query.filter_by(customer_phone=phone).all()
    headers = ["رقم الأمر", "نوع السيارة", "اللوحة", "الحالة", "تاريخ الدخول"]
    data = [[v.order_no, v.car_type, v.plate_no, v.status_label,
             v.entry_date.strftime("%Y-%m-%d")] for v in vehicles]
    title = f"تقرير العميل - {phone}" if phone else "تقرير عميل"
    return render_template("reports/customer_search.html", title=title, headers=headers, rows=data, phone=phone)


@reports_bp.route("/view/<code>")
@login_required
def view_report(code):
    title, headers, data = _build_report(code)
    return render_template("reports/preview.html", title=title, headers=headers, rows=data, code=code)


@reports_bp.route("/export/<code>/excel")
@login_required
def export_excel(code):
    title, headers, data = _build_report(code)
    buf = export_to_excel(headers, data, sheet_title=title)
    return send_file(buf, as_attachment=True, download_name=f"{code}.xlsx",
                      mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@reports_bp.route("/export/<code>/pdf")
@login_required
def export_pdf(code):
    title, headers, data = _build_report(code)
    buf = export_to_pdf(title, headers, data, company_name=_company_name())
    return send_file(buf, as_attachment=True, download_name=f"{code}.pdf", mimetype="application/pdf")
