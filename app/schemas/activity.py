from pydantic import BaseModel, Field, ConfigDict


class ActivityCreate(BaseModel):
    package_id: int
    activity_name: str = Field(min_length=2, max_length=200)
    location: str | None = None
    duration: str | None = None
    price: float = Field(gt=0)
    capacity: int = Field(gt=0)


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    package_id: int
    activity_name: str
    location: str | None
    duration: str | None
    price: float
    capacity: int
    booked_count: int
