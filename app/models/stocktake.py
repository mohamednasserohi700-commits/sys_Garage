from datetime import datetime
from app.extensions import db


class StockTake(db.Model):
    __tablename__ = "stock_takes"

    id = db.Column(db.Integer, primary_key=True)
    take_no = db.Column(db.String(30), unique=True, nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    take_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_closed = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    warehouse = db.relationship("Warehouse")
    items = db.relationship("StockTakeItem", back_populates="stocktake", cascade="all, delete-orphan")


class StockTakeItem(db.Model):
    __tablename__ = "stock_take_items"

    id = db.Column(db.Integer, primary_key=True)
    stocktake_id = db.Column(db.Integer, db.ForeignKey("stock_takes.id"), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    book_quantity = db.Column(db.Integer, nullable=False)     # الكمية الدفترية
    actual_quantity = db.Column(db.Integer, nullable=False)   # الكمية الفعلية

    stocktake = db.relationship("StockTake", back_populates="items")
    part = db.relationship("Part")

    @property
    def difference(self):
        return self.actual_quantity - self.book_quantity
