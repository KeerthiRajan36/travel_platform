from sqlalchemy import String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Hotel(Base):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(primary_key=True)
    hotel_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id"), nullable=False)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    rating: Mapped[float] = mapped_column(Integer, nullable=True)
    contact_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    destination: Mapped["Destination"] = relationship("Destination", back_populates="hotels")
    rooms: Mapped[list["Room"]] = relationship("Room", back_populates="hotel", cascade="all, delete-orphan")
