import enum
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Enum, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DestinationStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Destination(Base):
    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    best_season: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[DestinationStatus] = mapped_column(Enum(DestinationStatus), default=DestinationStatus.ACTIVE)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    packages: Mapped[list["TourPackage"]] = relationship("TourPackage", back_populates="destination")
    hotels: Mapped[list["Hotel"]] = relationship("Hotel", back_populates="destination")
