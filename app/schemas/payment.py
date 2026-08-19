from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from app.models.payment import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    payment_method: PaymentMethod
    transaction_id: str = Field(min_length=3, max_length=100)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    amount: float
    payment_method: PaymentMethod
    transaction_id: str
    payment_status: PaymentStatus
    payment_date: datetime
    refunded_amount: float


class RefundRequest(BaseModel):
    amount: float | None = Field(default=None, gt=0, description="Defaults to full remaining paid amount")
    reason: str | None = None
