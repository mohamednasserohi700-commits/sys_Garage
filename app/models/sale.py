from datetime import datetime
from app.extensions import db


class SaleInvoice(db.Model):
    __tablename__ = "sale_invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(30), unique=True, nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"))
    customer_name = db.Column(db.String(150))
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    tax_percent = db.Column(db.Numeric(5, 2), default=15)
    discount = db.Column(db.Numeric(12, 2), default=0)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    vehicle = db.relationship("Vehicle")
    items = db.relationship("SaleInvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    @property
    def subtotal(self):
        return float(sum((i.quantity * i.unit_price for i in self.items), 0))

    @property
    def total(self):
        sub = self.subtotal - float(self.discount or 0)
        return sub + (sub * float(self.tax_percent or 0) / 100)


class SaleInvoiceItem(db.Model):
    __tablename__ = "sale_invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("sale_invoices.id"), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)

    invoice = db.relationship("SaleInvoice", back_populates="items")
    part = db.relationship("Part")
