from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Cancellation(Base):
    __tablename__ = "cancellations"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True, nullable=False)
    cancellation_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    days_before_tour: Mapped[int] = mapped_column(Numeric(10, 0), nullable=False)
    refund_percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    refund_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    booking: Mapped["Booking"] = relationship("Booking", back_populates="cancellation")
