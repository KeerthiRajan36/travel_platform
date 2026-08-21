from fastapi import APIRouter, Depends, Query, status, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.payment import Payment, PaymentStatus
from app.models.booking import Booking
from app.schemas.payment import PaymentCreate, PaymentOut, RefundRequest
from app.schemas.common import PaginatedResponse
from app.auth.dependencies import require_operations, get_current_user
from app.models.user import User
from app.utils.exceptions import NotFoundError
from app.utils.pagination import paginate
from app.services import payment_service, notification_service
from app.websockets.manager import broadcast_booking_status

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/{booking_id}", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def make_payment(
    booking_id: int,
    payload: PaymentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_operations),
):
    payment = payment_service.create_payment(
        db, booking_id, payload.amount, payload.payment_method, payload.transaction_id
    )
    if payment.payment_status == PaymentStatus.SUCCESS:
        background_tasks.add_task(notification_service.notify_payment_success, current_user.id, booking_id, float(payment.amount))
        background_tasks.add_task(notification_service.notify_booking_confirmation, current_user.id, booking_id)
        current_booking_status = db.get(Booking, booking_id).booking_status.value
        background_tasks.add_task(
            broadcast_booking_status, booking_id, current_booking_status, {"event": "payment_received", "amount": float(payment.amount)}
        )
    else:
        background_tasks.add_task(notification_service.notify_payment_failure, current_user.id, booking_id)
        background_tasks.add_task(broadcast_booking_status, booking_id, "payment_failed")
    return payment


@router.get("", response_model=PaginatedResponse[PaymentOut])
def list_payments(
    db: Session = Depends(get_db),
    booking_id: int | None = Query(None),
    payment_status: PaymentStatus | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    _=Depends(require_operations),
):
    stmt = select(Payment)
    if booking_id:
        stmt = stmt.where(Payment.booking_id == booking_id)
    if payment_status:
        stmt = stmt.where(Payment.payment_status == payment_status)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(stmt.offset((page - 1) * limit).limit(limit)).scalars().all()
    return paginate(items, total, page, limit, PaymentOut)


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db), _=Depends(require_operations)):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise NotFoundError("Payment not found")
    return payment


@router.post("/{payment_id}/refund", response_model=PaymentOut)
def refund_payment(
    payment_id: int,
    payload: RefundRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_operations),
):
    payment = payment_service.refund_payment(db, payment_id, payload.amount)
    background_tasks.add_task(
        notification_service.notify_refund_processing, current_user.id, payment.booking_id, float(payload.amount or payment.refunded_amount)
    )
    return payment
