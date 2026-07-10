from app.extensions import db


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    address = db.Column(db.String(250))
    tax_no = db.Column(db.String(50))          # الرقم الضريبي
    balance = db.Column(db.Numeric(14, 2), default=0)   # الرصيد (مستحق للمورد)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
