from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.package import TourPackage
from app.models.itinerary import Itinerary
from app.schemas.package import ItineraryCreate, ItineraryUpdate, ItineraryOut
from app.auth.dependencies import require_management
from app.utils.exceptions import NotFoundError, BadRequestError, ConflictError

router = APIRouter(tags=["Itinerary"])


@router.post("/packages/{package_id}/itinerary", response_model=ItineraryOut, status_code=status.HTTP_201_CREATED)
def create_itinerary_day(
    package_id: int, payload: ItineraryCreate, db: Session = Depends(get_db), _=Depends(require_management)
):
    package = db.get(TourPackage, package_id)
    if not package or package.is_deleted:
        raise NotFoundError("Tour package not found")

    if payload.day_number > package.duration_days:
        raise BadRequestError(
            f"day_number ({payload.day_number}) cannot exceed package duration ({package.duration_days} days)"
        )

    existing = db.execute(
        select(Itinerary).where(Itinerary.package_id == package_id, Itinerary.day_number == payload.day_number)
    ).scalar_one_or_none()
    if existing:
        raise ConflictError(f"Day {payload.day_number} already exists for this package")

    item = Itinerary(package_id=package_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/packages/{package_id}/itinerary", response_model=list[ItineraryOut])
def list_itinerary(package_id: int, db: Session = Depends(get_db)):
    package = db.get(TourPackage, package_id)
    if not package or package.is_deleted:
        raise NotFoundError("Tour package not found")
    stmt = select(Itinerary).where(Itinerary.package_id == package_id).order_by(Itinerary.day_number)
    return db.execute(stmt).scalars().all()


@router.put("/itinerary/{item_id}", response_model=ItineraryOut)
def update_itinerary_day(
    item_id: int, payload: ItineraryUpdate, db: Session = Depends(get_db), _=Depends(require_management)
):
    item = db.get(Itinerary, item_id)
    if not item:
        raise NotFoundError("Itinerary item not found")

    data = payload.model_dump(exclude_unset=True)
    new_day = data.get("day_number", item.day_number)
    package = db.get(TourPackage, item.package_id)

    if new_day > package.duration_days:
        raise BadRequestError(f"day_number cannot exceed package duration ({package.duration_days} days)")

    if new_day != item.day_number:
        existing = db.execute(
            select(Itinerary).where(Itinerary.package_id == item.package_id, Itinerary.day_number == new_day)
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Day {new_day} already exists for this package")

    new_start = data.get("start_time", item.start_time)
    new_end = data.get("end_time", item.end_time)
    if new_end <= new_start:
        raise BadRequestError("end_time must be after start_time")

    for field, value in data.items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/itinerary/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary_day(item_id: int, db: Session = Depends(get_db), _=Depends(require_management)):
    item = db.get(Itinerary, item_id)
    if not item:
        raise NotFoundError("Itinerary item not found")
    db.delete(item)
    db.commit()
