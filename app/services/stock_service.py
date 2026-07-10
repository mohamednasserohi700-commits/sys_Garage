from app.extensions import db
from app.models import StockBalance, StockMovement
from app.services.exceptions import InsufficientStockError


def get_or_create_balance(part_id: int, warehouse_id: int) -> StockBalance:
    bal = StockBalance.query.filter_by(part_id=part_id, warehouse_id=warehouse_id).first()
    if not bal:
        bal = StockBalance(part_id=part_id, warehouse_id=warehouse_id, quantity=0)
        db.session.add(bal)
        db.session.flush()
    return bal


def receive_stock(part_id: int, warehouse_id: int, quantity: int, movement_type: str,
                   reference_no: str, user_id: int, notes: str = None):
    """زيادة الرصيد (شراء / تحويل وارد / تسوية موجبة / جرد)"""
    if quantity <= 0:
        raise ValueError("الكمية يجب أن تكون أكبر من صفر")
    bal = get_or_create_balance(part_id, warehouse_id)
    bal.quantity += quantity
    db.session.add(StockMovement(
        part_id=part_id, warehouse_id=warehouse_id, movement_type=movement_type,
        quantity=quantity, reference_no=reference_no, notes=notes, user_id=user_id
    ))


def issue_stock(part_id: int, warehouse_id: int, quantity: int, movement_type: str,
                 reference_no: str, user_id: int, notes: str = None, part_name: str = ""):
    """إنقاص الرصيد مع منع الصرف عند عدم توفر الكمية"""
    if quantity <= 0:
        raise ValueError("الكمية يجب أن تكون أكبر من صفر")
    bal = get_or_create_balance(part_id, warehouse_id)
    if bal.quantity < quantity:
        raise InsufficientStockError(part_name or f"#{part_id}", bal.quantity, quantity)
    bal.quantity -= quantity
    db.session.add(StockMovement(
        part_id=part_id, warehouse_id=warehouse_id, movement_type=movement_type,
        quantity=-quantity, reference_no=reference_no, notes=notes, user_id=user_id
    ))


def transfer_stock(part_id: int, from_warehouse_id: int, to_warehouse_id: int,
                    quantity: int, reference_no: str, user_id: int, part_name: str = ""):
    """تحويل بين مخزنين: خصم من المصدر وإضافة للمستلم بشكل ذري"""
    issue_stock(part_id, from_warehouse_id, quantity, "transfer_out", reference_no, user_id,
                part_name=part_name)
    receive_stock(part_id, to_warehouse_id, quantity, "transfer_in", reference_no, user_id)


def adjust_stock(part_id: int, warehouse_id: int, quantity_diff: int, reason: str, user_id: int):
    """تسوية: quantity_diff موجب = زيادة، سالب = نقص"""
    if quantity_diff == 0:
        raise ValueError("قيمة التسوية لا يمكن أن تكون صفرًا")
    bal = get_or_create_balance(part_id, warehouse_id)
    if quantity_diff < 0 and bal.quantity < abs(quantity_diff):
        raise InsufficientStockError(f"#{part_id}", bal.quantity, abs(quantity_diff))
    bal.quantity += quantity_diff
    db.session.add(StockMovement(
        part_id=part_id, warehouse_id=warehouse_id, movement_type="adjustment",
        quantity=quantity_diff, reference_no=None, notes=reason, user_id=user_id
    ))
