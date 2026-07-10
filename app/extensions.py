from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import logging
import os

db = SQLAlchemy()
login_manager = LoginManager()


def setup_logging(app):
    """تهيئة تسجيل الأخطاء (Logging) إلى ملف"""
    log_dir = os.path.join(app.root_path, "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    handler = logging.FileHandler(os.path.join(log_dir, "app.log"), encoding="utf-8")
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]"
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
