import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, Numeric, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BookingStatus(str, enum.Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    package_id: Mapped[int] = mapped_column(ForeignKey("tour_packages.id"), nullable=False)
    booking_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    number_of_travelers: Mapped[int] = mapped_column(Integer, nullable=False)
    base_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    tax: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    booking_status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.PENDING, index=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="bookings")
    package: Mapped["TourPackage"] = relationship("TourPackage", back_populates="bookings")
    travelers: Mapped[list["Traveler"]] = relationship(
        "Traveler", back_populates="booking", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="booking")
    hotel_reservations: Mapped[list["HotelReservation"]] = relationship(
        "HotelReservation", back_populates="booking"
    )
    cancellation: Mapped["Cancellation"] = relationship(
        "Cancellation", back_populates="booking", uselist=False, cascade="all, delete-orphan"
    )
    review: Mapped["Review"] = relationship("Review", back_populates="booking", uselist=False)
