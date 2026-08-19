from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=30)
    address: str | None = None
    emergency_contact: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    emergency_contact: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: str
    address: str | None
    emergency_contact: str | None
    created_at: datetime


class TravelerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    date_of_birth: date
    gender: str
    passport_number: str
    nationality: str
    special_requirements: str | None = None


class TravelerUpdate(BaseModel):
    full_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    passport_number: str | None = None
    nationality: str | None = None
    special_requirements: str | None = None


class TravelerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    full_name: str
    date_of_birth: date
    gender: str
    passport_number: str
    nationality: str
    special_requirements: str | None
