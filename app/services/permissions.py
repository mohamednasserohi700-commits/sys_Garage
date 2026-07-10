from functools import wraps
from flask import abort
from flask_login import current_user


def permission_required(code: str, action: str = "view"):
    """
    Decorator يُستخدم فوق أي route للتحقق من صلاحية المستخدم الحالي
    على شاشة (code) وإجراء معين (view/add/edit/delete/print/export)
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_permission(code, action):
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator
