from datetime import date

from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.models.room import RoomAvailability


class HotelCreate(BaseModel):
    hotel_name: str = Field(min_length=2, max_length=200)
    destination_id: int
    address: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    contact_number: str | None = None


class HotelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hotel_name: str
    destination_id: int
    address: str | None
    rating: float | None
    contact_number: str | None


class RoomCreate(BaseModel):
    hotel_id: int
    room_type: str = Field(min_length=2, max_length=80)
    room_number: str
    price_per_night: float = Field(gt=0)
    capacity: int = Field(gt=0)
    availability_status: RoomAvailability = RoomAvailability.AVAILABLE


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hotel_id: int
    room_type: str
    room_number: str
    price_per_night: float
    capacity: int
    availability_status: RoomAvailability


class HotelReservationCreate(BaseModel):
    booking_id: int
    room_id: int
    check_in: date
    check_out: date
    number_of_rooms: int = Field(default=1, gt=0)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self


class HotelReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    room_id: int
    check_in: date
    check_out: date
    number_of_rooms: int
    total_amount: float
