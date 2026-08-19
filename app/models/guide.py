import enum
from datetime import date

from sqlalchemy import String, Enum, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GuideAvailability(str, enum.Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    INACTIVE = "inactive"


class TourGuide(Base):
    __tablename__ = "tour_guides"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(150), nullable=True)
    availability_status: Mapped[GuideAvailability] = mapped_column(
        Enum(GuideAvailability), default=GuideAvailability.AVAILABLE
    )

    assignments: Mapped[list["GuideAssignment"]] = relationship("GuideAssignment", back_populates="guide")


class GuideAssignment(Base):
    """Tracks which guide is assigned to which package for which date range,
    so we can detect overlapping tour assignments."""

    __tablename__ = "guide_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("tour_packages.id"), nullable=False)
    guide_id: Mapped[int] = mapped_column(ForeignKey("tour_guides.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    package: Mapped["TourPackage"] = relationship("TourPackage", back_populates="guide_assignments")
    guide: Mapped["TourGuide"] = relationship("TourGuide", back_populates="assignments")
