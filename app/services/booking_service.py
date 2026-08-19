from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.customer import Customer
from app.models.package import TourPackage, PackageStatus
from app.utils.exceptions import NotFoundError, BadRequestError, ConflictError
from app.schemas.booking import BookingCreate
from app.services.cache_service import cache_clear


def _get_customer_or_404(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer or customer.is_deleted:
        raise NotFoundError("Customer not found")
    return customer


def _get_package_or_404(db: Session, package_id: int) -> TourPackage:
    package = db.get(TourPackage, package_id)
    if not package or package.is_deleted:
        raise NotFoundError("Tour package not found")
    return package


def create_booking(db: Session, payload: BookingCreate) -> Booking:
    customer = _get_customer_or_404(db, payload.customer_id)
    package = _get_package_or_404(db, payload.package_id)

    if package.status == PackageStatus.CANCELLED:
        raise BadRequestError("Cannot book a cancelled package")
    if package.status == PackageStatus.COMPLETED:
        raise BadRequestError("Cannot book a completed package")
    if package.status not in (PackageStatus.PUBLISHED,):
        raise BadRequestError(f"Package is not open for booking (status={package.status.value})")

    if payload.number_of_travelers > package.available_slots:
        raise ConflictError(
            f"Not enough available slots. Requested={payload.number_of_travelers}, "
            f"available={package.available_slots}"
        )

    # Duplicate booking rule: a customer cannot hold more than one
    # active (Pending/Confirmed) booking for the same package.
    existing = db.execute(
        select(Booking).where(
            and_(
                Booking.customer_id == payload.customer_id,
                Booking.package_id == payload.package_id,
                Booking.booking_status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
                Booking.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError("Customer already has an active booking for this package")

    base_amount = float(package.base_price) * payload.number_of_travelers
    total_amount = base_amount + payload.tax - payload.discount
    if total_amount < 0:
        raise BadRequestError("Discount cannot exceed base amount plus tax")

    booking = Booking(
        customer_id=payload.customer_id,
        package_id=payload.package_id,
        number_of_travelers=payload.number_of_travelers,
        base_amount=base_amount,
        discount=payload.discount,
        tax=payload.tax,
        total_amount=total_amount,
        booking_status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    cache_clear("dashboard:summary")
    return booking


def confirm_booking(db: Session, booking: Booking) -> Booking:
    """Called when a payment succeeds. Reduces available slots and marks
    the package Full if capacity is exhausted."""
    if booking.booking_status == BookingStatus.CONFIRMED:
        return booking
    if booking.booking_status != BookingStatus.PENDING:
        raise BadRequestError(f"Cannot confirm a booking with status {booking.booking_status.value}")

    package = booking.package
    if booking.number_of_travelers > package.available_slots:
        raise ConflictError("Not enough available slots to confirm this booking")

    package.available_slots -= booking.number_of_travelers
    if package.available_slots <= 0:
        package.status = PackageStatus.FULL

    booking.booking_status = BookingStatus.CONFIRMED
    db.add_all([booking, package])
    db.commit()
    db.refresh(booking)
    cache_clear("dashboard:summary")
    return booking


def restore_slots(db: Session, booking: Booking) -> None:
    """Restores package slots after an eligible cancellation of a
    previously confirmed booking."""
    package = booking.package
    package.available_slots = min(package.max_capacity, package.available_slots + booking.number_of_travelers)
    if package.status == PackageStatus.FULL and package.available_slots > 0:
        package.status = PackageStatus.PUBLISHED
    db.add(package)


def simple_cancel_booking(db: Session, booking: Booking) -> Booking:
    """Level 6 style cancellation: no refund calculation, just marks the
    booking cancelled and restores slots if it had been confirmed."""
    if booking.booking_status == BookingStatus.CANCELLED:
        raise BadRequestError("Booking is already cancelled")
    if booking.booking_status == BookingStatus.COMPLETED:
        raise BadRequestError("Cannot cancel a completed booking")

    if booking.booking_status == BookingStatus.CONFIRMED:
        restore_slots(db, booking)

    booking.booking_status = BookingStatus.CANCELLED
    db.add(booking)
    db.commit()
    db.refresh(booking)
    cache_clear("dashboard:summary")
    return booking
