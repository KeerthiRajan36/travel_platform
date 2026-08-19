from datetime import date, datetime, time

from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.models.package import PackageStatus


class PackageCreate(BaseModel):
    package_name: str = Field(min_length=2, max_length=200)
    destination_id: int
    description: str | None = None
    duration_days: int = Field(gt=0)
    base_price: float = Field(gt=0)
    max_capacity: int = Field(gt=0)
    start_date: date
    end_date: date
    status: PackageStatus = PackageStatus.DRAFT

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class PackageUpdate(BaseModel):
    package_name: str | None = None
    destination_id: int | None = None
    description: str | None = None
    duration_days: int | None = Field(default=None, gt=0)
    base_price: float | None = Field(default=None, gt=0)
    max_capacity: int | None = Field(default=None, gt=0)
    start_date: date | None = None
    end_date: date | None = None
    status: PackageStatus | None = None


class PackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    package_name: str
    destination_id: int
    description: str | None
    duration_days: int
    base_price: float
    max_capacity: int
    available_slots: int
    start_date: date
    end_date: date
    status: PackageStatus
    created_at: datetime


class ItineraryCreate(BaseModel):
    day_number: int = Field(gt=0)
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    location: str | None = None
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ItineraryUpdate(BaseModel):
    day_number: int | None = None
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_time: time | None = None
    end_time: time | None = None


class ItineraryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    package_id: int
    day_number: int
    title: str
    description: str | None
    location: str | None
    start_time: time
    end_time: time
