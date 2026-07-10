from app.extensions import db


class CompanySettings(db.Model):
    __tablename__ = "company_settings"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), default="مركز الصيانة")
    logo_path = db.Column(db.String(255))
    phone = db.Column(db.String(30))
    address = db.Column(db.String(250))
    email = db.Column(db.String(120))
    commercial_register = db.Column(db.String(50))   # السجل التجاري
    tax_no = db.Column(db.String(50))                # الرقم الضريبي
    tax_percent_default = db.Column(db.Numeric(5, 2), default=15)
    invoice_prefix = db.Column(db.String(10), default="INV-")
    workorder_prefix = db.Column(db.String(10), default="WO-")
    next_invoice_no = db.Column(db.Integer, default=1)
    next_workorder_no = db.Column(db.Integer, default=1)
