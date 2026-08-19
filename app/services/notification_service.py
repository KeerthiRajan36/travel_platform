import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.notification import Notification, NotificationType

logger = logging.getLogger("notifications")


def _dispatch(user_id: int | None, ntype: NotificationType, message: str) -> None:
    # Each BackgroundTask needs its own DB session.
    db: Session = SessionLocal()
    try:
        notification = Notification(user_id=user_id, type=ntype, message=message, is_sent=True)
        db.add(notification)
        db.commit()
        logger.info("[NOTIFICATION] type=%s user_id=%s message=%s", ntype.value, user_id, message)
    finally:
        db.close()


def notify_booking_confirmation(user_id: int | None, booking_id: int) -> None:
    _dispatch(user_id, NotificationType.BOOKING_CONFIRMATION, f"Booking #{booking_id} confirmed.")


def notify_payment_success(user_id: int | None, booking_id: int, amount: float) -> None:
    _dispatch(
        user_id, NotificationType.PAYMENT_SUCCESS, f"Payment of {amount} received for booking #{booking_id}."
    )


def notify_payment_failure(user_id: int | None, booking_id: int) -> None:
    _dispatch(user_id, NotificationType.PAYMENT_FAILURE, f"Payment failed for booking #{booking_id}.")


def notify_tour_cancellation(user_id: int | None, booking_id: int) -> None:
    _dispatch(user_id, NotificationType.TOUR_CANCELLATION, f"Booking #{booking_id} has been cancelled.")


def notify_refund_processing(user_id: int | None, booking_id: int, amount: float) -> None:
    _dispatch(
        user_id, NotificationType.REFUND_PROCESSING, f"Refund of {amount} is being processed for booking #{booking_id}."
    )


def notify_upcoming_tour_reminder(user_id: int | None, booking_id: int) -> None:
    _dispatch(user_id, NotificationType.UPCOMING_TOUR_REMINDER, f"Reminder: your tour for booking #{booking_id} is coming up.")


def notify_hotel_reservation_confirmation(user_id: int | None, reservation_id: int) -> None:
    _dispatch(
        user_id,
        NotificationType.HOTEL_RESERVATION_CONFIRMATION,
        f"Hotel reservation #{reservation_id} confirmed.",
    )
