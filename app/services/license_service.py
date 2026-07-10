import base64
import hashlib
import hmac
import json
import os
import platform
import uuid
from datetime import datetime, timedelta

# مفتاح سري للتوقيع - يُفضّل ضبطه عبر متغير بيئة LICENSE_SECRET_KEY في بيئة الإنتاج
SECRET_KEY = os.environ.get("LICENSE_SECRET_KEY", "GARAGE-CENTER-LICENSE-SECRET-2026-CHANGE-ME").encode()

PLAN_DAYS = {
    "6months": 182,
    "year": 365,
}


def get_machine_fingerprint() -> str:
    """توليد بصمة فريدة للجهاز الحالي (تمنع نسخ المفتاح لجهاز آخر)"""
    raw = f"{platform.node()}-{uuid.getnode()}-{platform.system()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _sign(payload: bytes) -> str:
    sig = hmac.new(SECRET_KEY, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def generate_activation_key(company_name: str, machine_fingerprint: str, plan: str) -> str:
    """توليد مفتاح تفعيل مشفّر ومرتبط باسم الشركة وبصمة الجهاز (يُستخدم من قبل مزود النظام)"""
    if plan not in PLAN_DAYS:
        raise ValueError("خطة اشتراك غير معروفة")
    expires_at = datetime.utcnow() + timedelta(days=PLAN_DAYS[plan])
    data = {
        "c": company_name,
        "m": machine_fingerprint,
        "p": plan,
        "e": expires_at.strftime("%Y-%m-%d"),
    }
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = _sign(payload)
    return f"{payload_b64}.{signature}"


def verify_activation_key(key: str, machine_fingerprint: str):
    """
    التحقق من صحة مفتاح التفعيل:
    - التوقيع صحيح (لم يتم التلاعب بالمفتاح)
    - مرتبط ببصمة نفس الجهاز (منع النسخ)
    - لم ينتهِ تاريخ الصلاحية
    يعيد dict البيانات عند النجاح أو يرفع ValueError عند الفشل
    """
    try:
        payload_b64, signature = key.strip().split(".")
    except ValueError:
        raise ValueError("صيغة مفتاح التفعيل غير صحيحة")

    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload = base64.urlsafe_b64decode(padded.encode())

    expected_sig = _sign(payload)
    if not hmac.compare_digest(expected_sig, signature):
        raise ValueError("مفتاح التفعيل غير صالح (فشل التحقق من التوقيع)")

    data = json.loads(payload.decode("utf-8"))

    if data["m"] != machine_fingerprint:
        raise ValueError("هذا المفتاح مرتبط بجهاز آخر ولا يمكن استخدامه هنا")

    expires_at = datetime.strptime(data["e"], "%Y-%m-%d")
    if datetime.utcnow() > expires_at:
        raise ValueError("انتهت صلاحية مفتاح التفعيل")

    return data
