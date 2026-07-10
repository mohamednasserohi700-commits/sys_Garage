from datetime import datetime
from app.extensions import db


class WorkOrderPart(db.Model):
    """قطعة الغيار المركبة في السيارة (تُخصم تلقائيًا من المخزن)"""
    __tablename__ = "work_order_parts"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False)     # سعر التكلفة وقت الصرف
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)    # سعر البيع
    technician_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vehicle = db.relationship("Vehicle", back_populates="parts_used")
    part = db.relationship("Part")
    warehouse = db.relationship("Warehouse")
    technician = db.relationship("User")

    @property
    def total_cost(self):
        return self.quantity * float(self.unit_cost)

    @property
    def total_price(self):
        return self.quantity * float(self.unit_price)
