import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _normalize_db_url(url: str) -> str:
    """Railway/Heroku تعطي رابط postgres:// القديم، وSQLAlchemy الحديث يتطلب postgresql://"""
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    """الإعدادات العامة للتطبيق"""
    SECRET_KEY = os.environ.get("SECRET_KEY", "garage-secret-key-change-in-production")

    # قاعدة البيانات: SQLite افتراضيًا للتشغيل المحلي.
    # على Railway: أضف خدمة PostgreSQL وسيقوم Railway تلقائيًا بضبط DATABASE_URL
    _raw_db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'garage.db')}")
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(_raw_db_url)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB لحجم الصور

    LANGUAGES = ["ar"]
    JSON_AS_ASCII = False

    LOW_STOCK_ALERT_ENABLED = True
