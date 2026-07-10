from datetime import datetime
from app.extensions import db


class StockAdjustment(db.Model):
    __tablename__ = "stock_adjustments"

    id = db.Column(db.Integer, primary_key=True)
    adjustment_no = db.Column(db.String(30), unique=True, nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)   # موجب زيادة / سالب نقص
    reason = db.Column(db.String(250), nullable=False)  # سبب التسوية
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    part = db.relationship("Part")
    warehouse = db.relationship("Warehouse")
    user = db.relationship("User")
