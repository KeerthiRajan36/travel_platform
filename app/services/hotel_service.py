from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.room import Room, RoomAvailability
from app.models.hotel_reservation import HotelReservation
from app.models.booking import Booking
from app.utils.exceptions import NotFoundError, BadRequestError, ConflictError
from app.schemas.hotel import HotelReservationCreate


def create_hotel_reservation(db: Session, payload: HotelReservationCreate) -> HotelReservation:
    booking = db.get(Booking, payload.booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError("Booking not found")

    room = db.get(Room, payload.room_id)
    if not room:
        raise NotFoundError("Room not found")
    if room.availability_status == RoomAvailability.UNAVAILABLE:
        raise BadRequestError("Room is marked unavailable")

    total_capacity = room.capacity * payload.number_of_rooms
    if booking.number_of_travelers > total_capacity:
        raise BadRequestError(
            f"Room capacity insufficient for {booking.number_of_travelers} travelers "
            f"(capacity available={total_capacity})"
        )

    # Prevent overlapping reservations for the same room.
    overlap = db.execute(
        select(HotelReservation).where(
            and_(
                HotelReservation.room_id == payload.room_id,
                HotelReservation.check_in < payload.check_out,
                HotelReservation.check_out > payload.check_in,
            )
        )
    ).scalar_one_or_none()
    if overlap:
        raise ConflictError("Room is already reserved for an overlapping date range")

    nights = (payload.check_out - payload.check_in).days
    total_amount = float(room.price_per_night) * nights * payload.number_of_rooms

    reservation = HotelReservation(
        booking_id=payload.booking_id,
        room_id=payload.room_id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        number_of_rooms=payload.number_of_rooms,
        total_amount=total_amount,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation
