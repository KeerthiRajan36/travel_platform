from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.models.traveler import Traveler
from app.schemas.customer import TravelerCreate, TravelerUpdate, TravelerOut
from app.auth.dependencies import require_operations
from app.utils.exceptions import NotFoundError, BadRequestError

router = APIRouter(tags=["Travelers"])


@router.post("/bookings/{booking_id}/travelers", response_model=TravelerOut, status_code=status.HTTP_201_CREATED)
def add_traveler(
    booking_id: int, payload: TravelerCreate, db: Session = Depends(get_db), _=Depends(require_operations)
):
    booking = db.get(Booking, booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError("Booking not found")

    existing_count = db.execute(select(Traveler).where(Traveler.booking_id == booking_id)).scalars().all()
    if len(existing_count) >= booking.number_of_travelers:
        raise BadRequestError(
            f"Booking already has the maximum of {booking.number_of_travelers} travelers registered"
        )

    traveler = Traveler(booking_id=booking_id, **payload.model_dump())
    db.add(traveler)
    db.commit()
    db.refresh(traveler)
    return traveler


@router.get("/bookings/{booking_id}/travelers", response_model=list[TravelerOut])
def list_travelers(booking_id: int, db: Session = Depends(get_db), _=Depends(require_operations)):
    booking = db.get(Booking, booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError("Booking not found")
    stmt = select(Traveler).where(Traveler.booking_id == booking_id)
    return db.execute(stmt).scalars().all()


@router.put("/travelers/{traveler_id}", response_model=TravelerOut)
def update_traveler(
    traveler_id: int, payload: TravelerUpdate, db: Session = Depends(get_db), _=Depends(require_operations)
):
    traveler = db.get(Traveler, traveler_id)
    if not traveler:
        raise NotFoundError("Traveler not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(traveler, field, value)
    db.add(traveler)
    db.commit()
    db.refresh(traveler)
    return traveler
