from datetime import datetime
from app.extensions import db


class VehicleStatusEnum:
    IN_PROGRESS = "under_maintenance"   # تحت الصيانة
    FINISHED = "finished"               # تم الانتهاء
    DELIVERED = "delivered"             # تم التسليم
    WAITING_PARTS = "waiting_parts"     # بانتظار قطع غيار

    LABELS_AR = {
        IN_PROGRESS: "تحت الصيانة",
        FINISHED: "تم الانتهاء",
        DELIVERED: "تم التسليم",
        WAITING_PARTS: "بانتظار قطع غيار",
    }


class Vehicle(db.Model):
    """أمر صيانة / بطاقة سيارة"""
    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(30), unique=True, nullable=False, index=True)  # رقم أمر الصيانة

    customer_name = db.Column(db.String(150), nullable=False)
    customer_phone = db.Column(db.String(30), nullable=False)
    customer_address = db.Column(db.String(250))

    car_type = db.Column(db.String(100), nullable=False)     # نوع السيارة
    car_model = db.Column(db.String(100))                    # الموديل
    plate_no = db.Column(db.String(30), nullable=False)      # رقم اللوحة
    chassis_no = db.Column(db.String(60))                    # رقم الشاسيه
    color = db.Column(db.String(40))
    odometer = db.Column(db.Integer, default=0)              # العداد

    entry_date = db.Column(db.DateTime, default=datetime.utcnow)
    expected_delivery_date = db.Column(db.DateTime)
    actual_delivery_date = db.Column(db.DateTime)

    technician_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    status = db.Column(db.String(30), default=VehicleStatusEnum.IN_PROGRESS)
    notes = db.Column(db.Text)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    technician = db.relationship("User", foreign_keys=[technician_id])
    faults = db.relationship("VehicleFault", back_populates="vehicle", cascade="all, delete-orphan")
    parts_used = db.relationship("WorkOrderPart", back_populates="vehicle", cascade="all, delete-orphan")

    @property
    def status_label(self):
        return VehicleStatusEnum.LABELS_AR.get(self.status, self.status)

    @property
    def total_parts_cost(self):
        return sum((p.quantity * p.unit_cost for p in self.parts_used), 0)

    @property
    def total_parts_sale(self):
        return sum((p.quantity * p.unit_price for p in self.parts_used), 0)


class VehicleFault(db.Model):
    """الأعطال المسجلة لكل سيارة"""
    __tablename__ = "vehicle_faults"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    description = db.Column(db.String(500), nullable=False)   # وصف العطل
    technician_notes = db.Column(db.Text)                      # ملاحظات الفني
    image_path = db.Column(db.String(255))                     # صورة اختيارية
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vehicle = db.relationship("Vehicle", back_populates="faults")
