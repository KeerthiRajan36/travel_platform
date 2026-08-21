from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.models.cancellation import Cancellation
from app.utils.exceptions import NotFoundError, BadRequestError
from app.services import booking_service
from app.services.cache_service import cache_clear


def _refund_percentage_for(days_before_tour: int) -> float:

    if days_before_tour >= 15:
        return 90.0
    if 7 <= days_before_tour <= 14:
        return 70.0
    if 2 <= days_before_tour <= 6:
        return 40.0
    return 0.0


def cancel_booking_with_refund(db: Session, booking_id: int, reason: str | None) -> Cancellation:
    booking = db.get(Booking, booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError("Booking not found")
    if booking.booking_status == BookingStatus.CANCELLED:
        raise BadRequestError("Booking is already cancelled")
    if booking.booking_status == BookingStatus.COMPLETED:
        raise BadRequestError("Cannot cancel a completed booking")

    existing = db.execute(select(Cancellation).where(Cancellation.booking_id == booking_id)).scalar_one_or_none()
    if existing:
        raise BadRequestError("A cancellation record already exists for this booking")

    package = booking.package
    days_before_tour = (package.start_date - date.today()).days
    refund_percentage = _refund_percentage_for(days_before_tour)

    # Refund pool = amount actually paid (successful payments) minus what
    # has already been refunded on those payments.
    successful_payments = db.execute(
        select(Payment)
        .where(Payment.booking_id == booking_id, Payment.payment_status.in_([PaymentStatus.SUCCESS, PaymentStatus.REFUNDED]))
        .order_by(Payment.payment_date.asc())
    ).scalars().all()

    refundable_pool = sum(float(p.amount) - float(p.refunded_amount) for p in successful_payments)
    refund_amount = round(refundable_pool * refund_percentage / 100, 2)

    # Apply the refund across payments, oldest first.
    remaining_to_refund = refund_amount
    for p in successful_payments:
        if remaining_to_refund <= 0:
            break
        refundable_on_this = float(p.amount) - float(p.refunded_amount)
        take = min(refundable_on_this, remaining_to_refund)
        if take <= 0:
            continue
        p.refunded_amount = float(p.refunded_amount) + take
        if p.refunded_amount >= float(p.amount) - 1e-6:
            p.payment_status = PaymentStatus.REFUNDED
        remaining_to_refund -= take
        db.add(p)

    # Restore package slots if the booking had been confirmed.
    if booking.booking_status == BookingStatus.CONFIRMED:
        booking_service.restore_slots(db, booking)

    booking.booking_status = BookingStatus.CANCELLED
    db.add(booking)

    cancellation = Cancellation(
        booking_id=booking_id,
        reason=reason,
        days_before_tour=max(days_before_tour, 0),
        refund_percentage=refund_percentage,
        refund_amount=refund_amount,
    )
    db.add(cancellation)
    db.commit()
    db.refresh(cancellation)
    cache_clear("dashboard:summary")
    return cancellation
