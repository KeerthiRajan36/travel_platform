from fastapi import APIRouter, Depends, Query, status, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.schemas.booking import BookingCreate, BookingOut, BookingCancelRequest
from app.schemas.cancellation import CancellationOut
from app.schemas.common import PaginatedResponse
from app.auth.dependencies import require_operations, get_current_user
from app.models.user import User
from app.utils.exceptions import NotFoundError
from app.utils.pagination import paginate
from app.services import booking_service, cancellation_service, notification_service
from app.websockets.manager import broadcast_booking_status

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    _=Depends(require_operations),
):
    booking = booking_service.create_booking(db, payload)
    return booking


@router.get("", response_model=PaginatedResponse[BookingOut])
def list_bookings(
    db: Session = Depends(get_db),
    customer_id: int | None = Query(None),
    package_id: int | None = Query(None),
    booking_status: BookingStatus | None = Query(None),
    payment_status: PaymentStatus | None = Query(None, description="Filter by latest payment status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("booking_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    _=Depends(require_operations),
):
    stmt = select(Booking).where(Booking.is_deleted.is_(False))
    if customer_id:
        stmt = stmt.where(Booking.customer_id == customer_id)
    if package_id:
        stmt = stmt.where(Booking.package_id == package_id)
    if booking_status:
        stmt = stmt.where(Booking.booking_status == booking_status)
    if payment_status:
        stmt = stmt.join(Payment, Payment.booking_id == Booking.id).where(Payment.payment_status == payment_status)

    sort_column = getattr(Booking, sort_by, Booking.booking_date)
    stmt = stmt.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(stmt.offset((page - 1) * limit).limit(limit)).scalars().all()
    return paginate(items, total, page, limit, BookingOut)


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: Session = Depends(get_db), _=Depends(require_operations)):
    booking = db.get(Booking, booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError("Booking not found")
    return booking


@router.put("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking_simple(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_operations),
):
    """Level 6 style cancellation: marks the booking cancelled and restores
    package slots if it had been confirmed. Does NOT calculate a refund —
    use POST /bookings/{booking_id}/cancel for the full refund engine."""
    booking = db.get(Booking, booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError("Booking not found")
    booking = booking_service.simple_cancel_booking(db, booking)
    background_tasks.add_task(notification_service.notify_tour_cancellation, current_user.id, booking.id)
    background_tasks.add_task(broadcast_booking_status, booking.id, booking.booking_status.value)
    return booking


@router.post("/{booking_id}/cancel", response_model=CancellationOut)
def cancel_booking_with_refund(
    booking_id: int,
    payload: BookingCancelRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_operations),
):
    """Level 10 Cancellation & Refund Engine: computes the refund
    automatically based on how many days remain before the tour start
    date, applies it to successful payments, restores package slots and
    creates a Cancellation history record."""
    cancellation = cancellation_service.cancel_booking_with_refund(db, booking_id, payload.reason)
    background_tasks.add_task(notification_service.notify_tour_cancellation, current_user.id, booking_id)
    background_tasks.add_task(broadcast_booking_status, booking_id, "Cancelled", {"refund_amount": float(cancellation.refund_amount)})
    if cancellation.refund_amount > 0:
        background_tasks.add_task(
            notification_service.notify_refund_processing, current_user.id, booking_id, cancellation.refund_amount
        )
    return cancellation
