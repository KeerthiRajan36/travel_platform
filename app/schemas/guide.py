from datetime import date

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.guide import GuideAvailability


class GuideCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str
    specialization: str | None = None
    availability_status: GuideAvailability = GuideAvailability.AVAILABLE


class GuideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: str
    specialization: str | None
    availability_status: GuideAvailability


class GuideAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    package_id: int
    guide_id: int
    start_date: date
    end_date: date
