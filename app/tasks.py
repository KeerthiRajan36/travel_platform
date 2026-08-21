import datetime
import logging

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.booking import Booking, BookingStatus
from app.models.package import TourPackage
from app.services import notification_service

logger = logging.getLogger("celery_tasks")


@celery_app.task(name="app.tasks.send_upcoming_tour_reminders")
def send_upcoming_tour_reminders(days_ahead: int = 3) -> int:
    """Finds confirmed bookings whose package starts exactly `days_ahead`
    days from now and sends a reminder notification for each. Intended to
    run daily via Celery beat (see the beat_schedule in app/celery_app.py)."""
    db = SessionLocal()
    sent = 0
    try:
        target_date = datetime.date.today() + datetime.timedelta(days=days_ahead)
        bookings = (
            db.query(Booking)
            .join(TourPackage, Booking.package_id == TourPackage.id)
            .filter(Booking.booking_status == BookingStatus.CONFIRMED)
            .filter(TourPackage.start_date == target_date)
            .all()
        )
        for booking in bookings:
            notification_service.notify_upcoming_tour_reminder(None, booking.id)
            sent += 1
        logger.info("Sent %s upcoming tour reminder(s) for tours starting %s", sent, target_date)
        return sent
    finally:
        db.close()
