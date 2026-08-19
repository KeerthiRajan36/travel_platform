from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    customer_id: int
    package_id: int
    number_of_travelers: int = Field(gt=0)
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    package_id: int
    booking_date: datetime
    number_of_travelers: int
    base_amount: float
    discount: float
    tax: float
    total_amount: float
    booking_status: BookingStatus


class BookingCancelRequest(BaseModel):
    reason: str | None = None
