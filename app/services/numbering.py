from datetime import datetime


def generate_doc_no(prefix: str, seq: int) -> str:
    """توليد رقم مستند مثل WO-20260709-0001"""
    today = datetime.utcnow().strftime("%Y%m%d")
    return f"{prefix}{today}-{seq:04d}"
