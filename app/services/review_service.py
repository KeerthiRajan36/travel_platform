from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.review import Review
from app.utils.exceptions import NotFoundError, BadRequestError, ConflictError
from app.schemas.review import ReviewCreate


def create_review(db: Session, customer_id: int, payload: ReviewCreate) -> Review:
    booking = db.get(Booking, payload.booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError("Booking not found")

    if booking.customer_id != customer_id:
        raise BadRequestError("You can only review your own bookings")

    if booking.booking_status != BookingStatus.COMPLETED:
        raise BadRequestError("Only customers with completed bookings can leave a review")

    if booking.review is not None:
        raise ConflictError("A review already exists for this booking")

    review = Review(
        customer_id=customer_id,
        package_id=booking.package_id,
        booking_id=booking.id,
        rating=payload.rating,
        review_text=payload.review_text,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
