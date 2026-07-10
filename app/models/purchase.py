from datetime import datetime
from app.extensions import db


class PurchaseInvoice(db.Model):
    __tablename__ = "purchase_invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(30), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    discount = db.Column(db.Numeric(12, 2), default=0)
    tax_percent = db.Column(db.Numeric(5, 2), default=15)
    notes = db.Column(db.String(250))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    supplier = db.relationship("Supplier")
    warehouse = db.relationship("Warehouse")
    items = db.relationship("PurchaseInvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    @property
    def subtotal(self):
        return float(sum((i.quantity * i.unit_price for i in self.items), 0))

    @property
    def tax_amount(self):
        return (self.subtotal - float(self.discount or 0)) * float(self.tax_percent or 0) / 100

    @property
    def total(self):
        return (self.subtotal - float(self.discount or 0)) + self.tax_amount


class PurchaseInvoiceItem(db.Model):
    __tablename__ = "purchase_invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("purchase_invoices.id"), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)

    invoice = db.relationship("PurchaseInvoice", back_populates="items")
    part = db.relationship("Part")

    @property
    def total(self):
        return self.quantity * float(self.unit_price)
