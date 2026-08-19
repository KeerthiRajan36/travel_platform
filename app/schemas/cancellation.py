from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CancellationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    cancellation_date: datetime
    reason: str | None
    days_before_tour: int
    refund_percentage: float
    refund_amount: float
