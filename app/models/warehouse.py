from datetime import datetime
from app.extensions import db


class Warehouse(db.Model):
    """المخزن"""
    __tablename__ = "warehouses"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    manager_name = db.Column(db.String(100))
    address = db.Column(db.String(250))
    is_active = db.Column(db.Boolean, default=True)

    balances = db.relationship("StockBalance", back_populates="warehouse")


class StockBalance(db.Model):
    """رصيد كل قطعة داخل كل مخزن (Materialized Balance للأداء)"""
    __tablename__ = "stock_balances"

    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)

    part = db.relationship("Part", back_populates="balances")
    warehouse = db.relationship("Warehouse", back_populates="balances")

    __table_args__ = (db.UniqueConstraint("part_id", "warehouse_id", name="uq_part_warehouse"),)


class StockMovement(db.Model):
    """سجل حركات المخزون (وارد/منصرف) لكل الأسباب: صرف لأمر صيانة، شراء، تحويل، تسوية، جرد"""
    __tablename__ = "stock_movements"

    MOVEMENT_TYPES_AR = {
        "in_purchase": "وارد شراء",
        "out_workorder": "منصرف صيانة",
        "transfer_in": "تحويل وارد",
        "transfer_out": "تحويل صادر",
        "adjustment": "تسوية",
        "stocktake": "جرد",
        "sale": "منصرف بيع",
    }

    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    movement_type = db.Column(db.String(30), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)     # موجب = وارد، سالب = منصرف
    reference_no = db.Column(db.String(50))              # رقم المستند المرجعي
    notes = db.Column(db.String(250))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    part = db.relationship("Part")
    warehouse = db.relationship("Warehouse")
    user = db.relationship("User")

    @property
    def type_label(self):
        return self.MOVEMENT_TYPES_AR.get(self.movement_type, self.movement_type)
