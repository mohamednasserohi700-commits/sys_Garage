class BusinessError(Exception):
    """خطأ منطق أعمال يُعرض رسالته مباشرة للمستخدم"""
    pass


class InsufficientStockError(BusinessError):
    def __init__(self, part_name, available, requested):
        super().__init__(
            f"الكمية غير متوفرة للقطعة '{part_name}': المتاح {available}، المطلوب {requested}"
        )
