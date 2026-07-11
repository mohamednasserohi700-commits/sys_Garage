from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Vehicle, VehicleFault, VehicleStatusEnum, User, Part, Warehouse, \
    WorkOrderPart, CompanySettings
from app.services import stock_service
from app.services.exceptions import BusinessError
from app.services.numbering import generate_doc_no
from app.services.permissions import permission_required

vehicles_bp = Blueprint("vehicles", __name__, template_folder="../../templates/vehicles")


def _next_order_no():
    settings = CompanySettings.query.first()
    prefix = settings.workorder_prefix if settings else "WO-"
    seq = settings.next_workorder_no if settings else 1
    if settings:
        settings.next_workorder_no += 1
        db.session.commit()
    return generate_doc_no(prefix, seq)


@vehicles_bp.route("/")
@login_required
def list_vehicles():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    query = Vehicle.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Vehicle.order_no.like(like),
                Vehicle.customer_name.like(like),
                Vehicle.customer_phone.like(like),
                Vehicle.plate_no.like(like),
                Vehicle.chassis_no.like(like),
            )
        )
    if status:
        query = query.filter_by(status=status)
    vehicles = query.order_by(Vehicle.created_at.desc()).all()
    return render_template("vehicles/list.html", vehicles=vehicles, q=q, status=status,
                            statuses=VehicleStatusEnum.LABELS_AR)


@vehicles_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_vehicle():
    technicians = User.query.filter_by(is_active_user=True, is_hidden=False).all()
    if request.method == "POST":
        try:
            v = Vehicle(
                order_no=_next_order_no(),
                customer_name=request.form["customer_name"].strip(),
                customer_phone=request.form["customer_phone"].strip(),
                customer_address=request.form.get("customer_address", "").strip(),
                car_type=request.form["car_type"].strip(),
                car_model=request.form.get("car_model", "").strip(),
                plate_no=request.form["plate_no"].strip(),
                chassis_no=request.form.get("chassis_no", "").strip(),
                color=request.form.get("color", "").strip(),
                odometer=int(request.form.get("odometer") or 0),
                expected_delivery_date=_parse_date(request.form.get("expected_delivery_date")),
                technician_id=request.form.get("technician_id") or None,
                notes=request.form.get("notes", "").strip(),
                created_by_id=current_user.id,
            )
            if not v.customer_name or not v.customer_phone or not v.car_type or not v.plate_no:
                raise BusinessError("الحقول (اسم العميل، الهاتف، نوع السيارة، رقم اللوحة) إلزامية")
            db.session.add(v)
            db.session.commit()
            flash(f"تم إنشاء أمر الصيانة {v.order_no} بنجاح", "success")
            return redirect(url_for("vehicles.view_vehicle", vehicle_id=v.id))
        except BusinessError as e:
            db.session.rollback()
            flash(str(e), "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"حدث خطأ غير متوقع: {e}", "danger")
            from app.services.notification_service import log_system_error
            log_system_error(f"خطأ عند إنشاء أمر صيانة: {e}")
    return render_template("vehicles/form.html", vehicle=None, technicians=technicians)


@vehicles_bp.route("/<int:vehicle_id>/edit", methods=["GET", "POST"])
@login_required
def edit_vehicle(vehicle_id):
    v = Vehicle.query.get_or_404(vehicle_id)
    technicians = User.query.filter_by(is_active_user=True, is_hidden=False).all()
    if request.method == "POST":
        try:
            v.customer_name = request.form["customer_name"].strip()
            v.customer_phone = request.form["customer_phone"].strip()
            v.customer_address = request.form.get("customer_address", "").strip()
            v.car_type = request.form["car_type"].strip()
            v.car_model = request.form.get("car_model", "").strip()
            v.plate_no = request.form["plate_no"].strip()
            v.chassis_no = request.form.get("chassis_no", "").strip()
            v.color = request.form.get("color", "").strip()
            v.odometer = int(request.form.get("odometer") or 0)
            v.expected_delivery_date = _parse_date(request.form.get("expected_delivery_date"))
            v.technician_id = request.form.get("technician_id") or None
            v.status = request.form.get("status", v.status)
            v.notes = request.form.get("notes", "").strip()
            if v.status in (VehicleStatusEnum.FINISHED, VehicleStatusEnum.DELIVERED) and not v.actual_delivery_date:
                v.actual_delivery_date = datetime.utcnow()
            db.session.commit()
            flash("تم تحديث بيانات السيارة بنجاح", "success")
            return redirect(url_for("vehicles.view_vehicle", vehicle_id=v.id))
        except Exception as e:
            db.session.rollback()
            flash(f"حدث خطأ: {e}", "danger")
            from app.services.notification_service import log_system_error
            log_system_error(f"خطأ عند تعديل أمر صيانة #{vehicle_id}: {e}")
    return render_template("vehicles/form.html", vehicle=v, technicians=technicians)


@vehicles_bp.route("/<int:vehicle_id>")
@login_required
def view_vehicle(vehicle_id):
    v = Vehicle.query.get_or_404(vehicle_id)
    parts = Part.query.filter_by(is_active=True).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    return render_template("vehicles/view.html", vehicle=v, parts=parts, warehouses=warehouses,
                            statuses=VehicleStatusEnum.LABELS_AR)


@vehicles_bp.route("/<int:vehicle_id>/delete", methods=["POST"])
@login_required
@permission_required("vehicles", "delete")
def delete_vehicle(vehicle_id):
    v = Vehicle.query.get_or_404(vehicle_id)
    db.session.delete(v)
    db.session.commit()
    flash("تم حذف أمر الصيانة", "success")
    return redirect(url_for("vehicles.list_vehicles"))


# ---------------- الأعطال ----------------
@vehicles_bp.route("/<int:vehicle_id>/faults/add", methods=["POST"])
@login_required
def add_fault(vehicle_id):
    v = Vehicle.query.get_or_404(vehicle_id)
    desc = request.form.get("description", "").strip()
    if not desc:
        flash("وصف العطل مطلوب", "danger")
        return redirect(url_for("vehicles.view_vehicle", vehicle_id=vehicle_id))
    fault = VehicleFault(
        vehicle_id=v.id,
        description=desc,
        technician_notes=request.form.get("technician_notes", "").strip(),
    )
    db.session.add(fault)
    db.session.commit()
    flash("تم تسجيل العطل", "success")
    return redirect(url_for("vehicles.view_vehicle", vehicle_id=vehicle_id))


@vehicles_bp.route("/faults/<int:fault_id>/delete", methods=["POST"])
@login_required
def delete_fault(fault_id):
    f = VehicleFault.query.get_or_404(fault_id)
    vid = f.vehicle_id
    db.session.delete(f)
    db.session.commit()
    flash("تم حذف العطل", "success")
    return redirect(url_for("vehicles.view_vehicle", vehicle_id=vid))


# ---------------- تركيب قطع الغيار ----------------
@vehicles_bp.route("/<int:vehicle_id>/parts/add", methods=["POST"])
@login_required
def add_part_to_vehicle(vehicle_id):
    v = Vehicle.query.get_or_404(vehicle_id)

    # يدعم إضافة أكثر من قطعة في نفس الوقت (part_id[], warehouse_id[], quantity[])
    # مع الحفاظ على التوافق مع الإرسال القديم لحقل واحد فقط
    part_ids = request.form.getlist("part_id[]") or request.form.getlist("part_id")
    warehouse_ids = request.form.getlist("warehouse_id[]") or request.form.getlist("warehouse_id")
    quantities = request.form.getlist("quantity[]") or request.form.getlist("quantity")

    if not part_ids:
        flash("يجب اختيار قطعة واحدة على الأقل", "danger")
        return redirect(url_for("vehicles.view_vehicle", vehicle_id=vehicle_id))

    added_count = 0
    try:
        for pid, wid, qty in zip(part_ids, warehouse_ids, quantities):
            if not pid or not wid or not qty:
                continue
            part_id = int(pid)
            warehouse_id = int(wid)
            quantity = int(qty)
            part = Part.query.get_or_404(part_id)

            if quantity <= 0:
                raise BusinessError(f"الكمية يجب أن تكون أكبر من صفر للقطعة '{part.name}'")

            # خصم تلقائي من المخزن (يمنع الصرف عند عدم توفر الكمية)
            stock_service.issue_stock(
                part_id=part_id, warehouse_id=warehouse_id, quantity=quantity,
                movement_type="out_workorder", reference_no=v.order_no,
                user_id=current_user.id, part_name=part.name,
            )

            wop = WorkOrderPart(
                vehicle_id=v.id, part_id=part_id, warehouse_id=warehouse_id, quantity=quantity,
                unit_cost=part.purchase_price, unit_price=part.sale_price,
                technician_id=current_user.id,
            )
            db.session.add(wop)
            added_count += 1

        if added_count == 0:
            raise BusinessError("يجب اختيار قطعة واحدة على الأقل")

        db.session.commit()
        flash(f"تم صرف {added_count} قطعة/قطع وربطها بأمر الصيانة", "success")
    except BusinessError as e:
        db.session.rollback()
        flash(str(e), "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"حدث خطأ: {e}", "danger")
        from app.services.notification_service import log_system_error
        log_system_error(f"خطأ عند تركيب قطع غيار على أمر صيانة #{vehicle_id}: {e}")
    return redirect(url_for("vehicles.view_vehicle", vehicle_id=vehicle_id))


@vehicles_bp.route("/parts/<int:wop_id>/delete", methods=["POST"])
@login_required
def remove_part_from_vehicle(wop_id):
    wop = WorkOrderPart.query.get_or_404(wop_id)
    vid = wop.vehicle_id
    # إعادة الكمية للمخزن عند إلغاء التركيب
    stock_service.receive_stock(
        part_id=wop.part_id, warehouse_id=wop.warehouse_id, quantity=wop.quantity,
        movement_type="adjustment", reference_no=f"إلغاء صرف - {wop.vehicle.order_no}",
        user_id=current_user.id, notes="إلغاء تركيب قطعة",
    )
    db.session.delete(wop)
    db.session.commit()
    flash("تم إلغاء تركيب القطعة وإعادتها للمخزون", "success")
    return redirect(url_for("vehicles.view_vehicle", vehicle_id=vid))


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
