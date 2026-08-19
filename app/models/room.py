import enum

from sqlalchemy import String, Integer, Numeric, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoomAvailability(str, enum.Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id"), nullable=False)
    room_type: Mapped[str] = mapped_column(String(80), nullable=False)
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)
    price_per_night: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    availability_status: Mapped[RoomAvailability] = mapped_column(
        Enum(RoomAvailability), default=RoomAvailability.AVAILABLE
    )

    hotel: Mapped["Hotel"] = relationship("Hotel", back_populates="rooms")
    reservations: Mapped[list["HotelReservation"]] = relationship("HotelReservation", back_populates="room")
