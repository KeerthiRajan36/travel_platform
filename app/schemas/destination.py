from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from app.models.destination import DestinationStatus


class DestinationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    country: str = Field(min_length=2, max_length=100)
    state: str | None = None
    description: str | None = None
    best_season: str | None = None
    status: DestinationStatus = DestinationStatus.ACTIVE


class DestinationUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    state: str | None = None
    description: str | None = None
    best_season: str | None = None
    status: DestinationStatus | None = None


class DestinationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str
    state: str | None
    description: str | None
    best_season: str | None
    status: DestinationStatus
    created_at: datetime
