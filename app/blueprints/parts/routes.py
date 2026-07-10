import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
import openpyxl

from app.extensions import db
from app.models import Part, PartCategory, Supplier

parts_bp = Blueprint("parts", __name__, template_folder="../../templates/parts")


def _generate_code():
    last = Part.query.order_by(Part.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"PRT-{next_id:05d}"


@parts_bp.route("/")
@login_required
def list_parts():
    q = request.args.get("q", "").strip()
    query = Part.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Part.name.like(like), Part.code.like(like), Part.barcode.like(like)))
    parts = query.order_by(Part.name).all()
    categories = PartCategory.query.all()
    return render_template("parts/list.html", parts=parts, q=q, categories=categories)


@parts_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_part():
    categories = PartCategory.query.all()
    suppliers = Supplier.query.filter_by(is_active=True).all()
    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            if not name:
                raise ValueError("اسم القطعة مطلوب")
            p = Part(
                code=_generate_code(),
                barcode=request.form.get("barcode", "").strip() or None,
                name=name,
                category_id=request.form.get("category_id") or None,
                unit=request.form.get("unit", "قطعة").strip(),
                min_quantity=int(request.form.get("min_quantity") or 1),
                purchase_price=float(request.form.get("purchase_price") or 0),
                sale_price=float(request.form.get("sale_price") or 0),
                supplier_id=request.form.get("supplier_id") or None,
            )
            db.session.add(p)
            db.session.commit()
            flash(f"تم إضافة القطعة بنجاح، الكود: {p.code}", "success")
            return redirect(url_for("parts.list_parts"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")
    return render_template("parts/form.html", part=None, categories=categories, suppliers=suppliers)


@parts_bp.route("/<int:part_id>/edit", methods=["GET", "POST"])
@login_required
def edit_part(part_id):
    p = Part.query.get_or_404(part_id)
    categories = PartCategory.query.all()
    suppliers = Supplier.query.filter_by(is_active=True).all()
    if request.method == "POST":
        try:
            p.name = request.form["name"].strip()
            p.barcode = request.form.get("barcode", "").strip() or None
            p.category_id = request.form.get("category_id") or None
            p.unit = request.form.get("unit", "قطعة").strip()
            p.min_quantity = int(request.form.get("min_quantity") or 1)
            p.purchase_price = float(request.form.get("purchase_price") or 0)
            p.sale_price = float(request.form.get("sale_price") or 0)
            p.supplier_id = request.form.get("supplier_id") or None
            p.is_active = bool(request.form.get("is_active"))
            db.session.commit()
            flash("تم تحديث بيانات القطعة", "success")
            return redirect(url_for("parts.list_parts"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "danger")
    return render_template("parts/form.html", part=p, categories=categories, suppliers=suppliers)


@parts_bp.route("/<int:part_id>/delete", methods=["POST"])
@login_required
def delete_part(part_id):
    p = Part.query.get_or_404(part_id)
    try:
        db.session.delete(p)
        db.session.commit()
        flash("تم حذف القطعة", "success")
    except Exception:
        db.session.rollback()
        flash("لا يمكن حذف هذه القطعة لوجود حركات مرتبطة بها، يمكنك إيقافها بدلاً من ذلك", "danger")
    return redirect(url_for("parts.list_parts"))


@parts_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_excel():
    """استيراد قطع الغيار من ملف Excel (أعمدة: الاسم، الفئة، الوحدة، أقل كمية، سعر الشراء، سعر البيع)"""
    if request.method == "POST":
        file = request.files.get("excel_file")
        if not file:
            flash("الرجاء اختيار ملف Excel", "danger")
            return redirect(url_for("parts.import_excel"))
        try:
            wb = openpyxl.load_workbook(file, data_only=True)
            ws = wb.active
            count = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not row[0]:
                    continue
                name = str(row[0]).strip()
                p = Part(
                    code=_generate_code(),
                    name=name,
                    unit=str(row[2]) if len(row) > 2 and row[2] else "قطعة",
                    min_quantity=int(row[3]) if len(row) > 3 and row[3] else 1,
                    purchase_price=float(row[4]) if len(row) > 4 and row[4] else 0,
                    sale_price=float(row[5]) if len(row) > 5 and row[5] else 0,
                )
                db.session.add(p)
                count += 1
            db.session.commit()
            flash(f"تم استيراد {count} قطعة بنجاح", "success")
            return redirect(url_for("parts.list_parts"))
        except Exception as e:
            db.session.rollback()
            flash(f"فشل الاستيراد: {e}", "danger")
    return render_template("parts/import.html")
