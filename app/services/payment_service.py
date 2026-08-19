from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.utils.exceptions import NotFoundError, BadRequestError, ConflictError
from app.services import booking_service
from app.services.cache_service import cache_clear


def _get_booking_or_404(db: Session, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError("Booking not found")
    return booking


def _successful_paid_total(db: Session, booking_id: int) -> float:
    stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.booking_id == booking_id, Payment.payment_status == PaymentStatus.SUCCESS
    )
    return float(db.execute(stmt).scalar_one())


def create_payment(
    db: Session, booking_id: int, amount: float, payment_method: PaymentMethod, transaction_id: str
) -> Payment:
    booking = _get_booking_or_404(db, booking_id)

    if booking.booking_status == BookingStatus.CANCELLED:
        raise BadRequestError("Cannot pay for a cancelled booking")

    # Prevent duplicate transactions.
    existing_txn = db.execute(select(Payment).where(Payment.transaction_id == transaction_id)).scalar_one_or_none()
    if existing_txn:
        raise ConflictError("A payment with this transaction_id already exists")

    already_paid = _successful_paid_total(db, booking_id)
    if already_paid + amount > float(booking.total_amount) + 1e-6:
        raise BadRequestError(
            f"Payment amount exceeds outstanding booking balance. "
            f"Outstanding={float(booking.total_amount) - already_paid:.2f}"
        )

    # For this simulated payment gateway, a payment is considered
    # successful immediately unless the amount is non-positive.
    status_ = PaymentStatus.SUCCESS if amount > 0 else PaymentStatus.FAILED

    payment = Payment(
        booking_id=booking_id,
        amount=amount,
        payment_method=payment_method,
        transaction_id=transaction_id,
        payment_status=status_,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    if status_ == PaymentStatus.SUCCESS:
        cache_clear("dashboard:summary")

    if status_ == PaymentStatus.SUCCESS:
        new_total_paid = already_paid + amount
        # Successful payment should confirm eligible (pending) bookings
        # once the outstanding balance is fully covered.
        if booking.booking_status == BookingStatus.PENDING and new_total_paid >= float(booking.total_amount) - 1e-6:
            booking_service.confirm_booking(db, booking)

    return payment


def refund_payment(db: Session, payment_id: int, amount: float | None) -> Payment:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise NotFoundError("Payment not found")
    if payment.payment_status != PaymentStatus.SUCCESS:
        raise BadRequestError("Only successful payments can be refunded")

    refund_amount = amount if amount is not None else float(payment.amount) - float(payment.refunded_amount)
    remaining = float(payment.amount) - float(payment.refunded_amount)
    if refund_amount > remaining + 1e-6:
        raise BadRequestError(f"Refund amount exceeds paid amount. Refundable={remaining:.2f}")
    if refund_amount <= 0:
        raise BadRequestError("Refund amount must be positive")

    payment.refunded_amount = float(payment.refunded_amount) + refund_amount
    if payment.refunded_amount >= float(payment.amount) - 1e-6:
        payment.payment_status = PaymentStatus.REFUNDED

    db.add(payment)
    db.commit()
    db.refresh(payment)
    cache_clear("dashboard:summary")
    return payment
