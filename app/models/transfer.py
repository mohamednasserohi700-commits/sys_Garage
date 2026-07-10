from datetime import datetime
from app.extensions import db


class StockTransfer(db.Model):
    __tablename__ = "stock_transfers"

    id = db.Column(db.Integer, primary_key=True)
    transfer_no = db.Column(db.String(30), unique=True, nullable=False)
    from_warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    to_warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    transfer_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.String(250))
    is_approved = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    from_warehouse = db.relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = db.relationship("Warehouse", foreign_keys=[to_warehouse_id])
    items = db.relationship("StockTransferItem", back_populates="transfer", cascade="all, delete-orphan")


class StockTransferItem(db.Model):
    __tablename__ = "stock_transfer_items"

    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey("stock_transfers.id"), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    transfer = db.relationship("StockTransfer", back_populates="items")
    part = db.relationship("Part")
