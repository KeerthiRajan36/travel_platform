import enum
from datetime import datetime, date, timezone

from sqlalchemy import String, DateTime, Date, Enum, Integer, Numeric, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PackageStatus(str, enum.Enum):
    DRAFT = "Draft"
    PUBLISHED = "Published"
    FULL = "Full"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class TourPackage(Base):
    __tablename__ = "tour_packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    available_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PackageStatus] = mapped_column(Enum(PackageStatus), default=PackageStatus.DRAFT, index=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    destination: Mapped["Destination"] = relationship("Destination", back_populates="packages")
    itinerary_days: Mapped[list["Itinerary"]] = relationship(
        "Itinerary", back_populates="package", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="package")
    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="package")
    guide_assignments: Mapped[list["GuideAssignment"]] = relationship("GuideAssignment", back_populates="package")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="package")
