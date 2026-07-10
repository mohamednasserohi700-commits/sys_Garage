from app.extensions import db


class PartCategory(db.Model):
    __tablename__ = "part_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    parts = db.relationship("Part", back_populates="category")


class Part(db.Model):
    """قطعة الغيار"""
    __tablename__ = "parts"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)  # كود تلقائي
    barcode = db.Column(db.String(60), unique=True)
    name = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("part_categories.id"))
    unit = db.Column(db.String(30), default="قطعة")           # الوحدة
    min_quantity = db.Column(db.Integer, default=1)            # أقل كمية (حد إعادة الطلب)
    purchase_price = db.Column(db.Numeric(12, 2), default=0)
    sale_price = db.Column(db.Numeric(12, 2), default=0)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    image_path = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)

    category = db.relationship("PartCategory", back_populates="parts")
    supplier = db.relationship("Supplier")
    balances = db.relationship("StockBalance", back_populates="part", cascade="all, delete-orphan")

    @property
    def total_balance(self):
        return sum((b.quantity for b in self.balances), 0)

    def balance_in_warehouse(self, warehouse_id):
        for b in self.balances:
            if b.warehouse_id == warehouse_id:
                return b.quantity
        return 0

    @property
    def is_low_stock(self):
        return self.total_balance <= self.min_quantity
