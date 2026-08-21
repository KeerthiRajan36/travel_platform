import enum
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationType(str, enum.Enum):
    BOOKING_CONFIRMATION = "booking_confirmation"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILURE = "payment_failure"
    TOUR_CANCELLATION = "tour_cancellation"
    REFUND_PROCESSING = "refund_processing"
    UPCOMING_TOUR_REMINDER = "upcoming_tour_reminder"
    HOTEL_RESERVATION_CONFIRMATION = "hotel_reservation_confirmation"


class Notification(Base):

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
