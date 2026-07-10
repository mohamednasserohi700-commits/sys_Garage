import os
from datetime import datetime
from flask import Flask, redirect, url_for, request, render_template
from flask_login import LoginManager, current_user

from config import Config
from app.extensions import db, login_manager, setup_logging


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "الرجاء تسجيل الدخول للمتابعة"
    login_manager.login_message_category = "warning"

    setup_logging(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ---------------- تسجيل الـ Blueprints ----------------
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.dashboard.routes import dashboard_bp
    from app.blueprints.vehicles.routes import vehicles_bp
    from app.blueprints.parts.routes import parts_bp
    from app.blueprints.warehouses.routes import warehouses_bp
    from app.blueprints.suppliers.routes import suppliers_bp
    from app.blueprints.purchases.routes import purchases_bp
    from app.blueprints.transfers.routes import transfers_bp
    from app.blueprints.stocktake.routes import stocktake_bp
    from app.blueprints.adjustments.routes import adjustments_bp
    from app.blueprints.reports.routes import reports_bp
    from app.blueprints.users.routes import users_bp
    from app.blueprints.settings.routes import settings_bp
    from app.blueprints.license.routes import license_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/")
    app.register_blueprint(vehicles_bp, url_prefix="/vehicles")
    app.register_blueprint(parts_bp, url_prefix="/parts")
    app.register_blueprint(warehouses_bp, url_prefix="/warehouses")
    app.register_blueprint(suppliers_bp, url_prefix="/suppliers")
    app.register_blueprint(purchases_bp, url_prefix="/purchases")
    app.register_blueprint(transfers_bp, url_prefix="/transfers")
    app.register_blueprint(stocktake_bp, url_prefix="/stocktake")
    app.register_blueprint(adjustments_bp, url_prefix="/adjustments")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    app.register_blueprint(license_bp, url_prefix="/license")

    # ---------------- التحقق من الترخيص قبل كل طلب ----------------
    @app.before_request
    def check_license():
        from app.models import License
        exempt_endpoints = {"license.activate", "license.status", "license.serials",
                             "license.delete_serial", "auth.login", "static"}
        if request.endpoint in exempt_endpoints or request.endpoint is None:
            return
        if current_user.is_authenticated and getattr(current_user, "is_super_admin", False):
            return
        lic = License.query.first()
        if not lic or lic.is_expired:
            return redirect(url_for("license.activate"))

    @app.context_processor
    def inject_company():
        from app.models import CompanySettings
        company = CompanySettings.query.first()
        return {"company": company}

    @app.context_processor
    def inject_license_status():
        from app.models import License
        lic = License.query.first()
        return {"license_days_remaining": lic.days_remaining if lic and not lic.is_expired else None}

    # ---------------- معالجة الأخطاء ----------------
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"Server Error: {e}")
        return render_template("errors/500.html"), 500

    return app
