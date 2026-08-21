from fastapi import APIRouter, Depends, Query, status, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hotel import Hotel
from app.models.room import Room
from app.models.hotel_reservation import HotelReservation
from app.schemas.hotel import (
    HotelCreate, HotelOut, RoomCreate, RoomOut, HotelReservationCreate, HotelReservationOut,
)
from app.schemas.common import PaginatedResponse
from app.auth.dependencies import require_management, require_operations, get_current_user
from app.models.user import User
from app.utils.exceptions import NotFoundError
from app.utils.pagination import paginate
from app.services import hotel_service, notification_service

router = APIRouter(tags=["Hotels"])


@router.post("/hotels", response_model=HotelOut, status_code=status.HTTP_201_CREATED)
def create_hotel(payload: HotelCreate, db: Session = Depends(get_db), _=Depends(require_management)):
    hotel = Hotel(**payload.model_dump())
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


@router.get("/hotels", response_model=PaginatedResponse[HotelOut])
def list_hotels(
    db: Session = Depends(get_db),
    destination_id: int | None = Query(None),
    min_rating: float | None = Query(None, ge=0, le=5),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    stmt = select(Hotel).where(Hotel.is_deleted.is_(False))
    if destination_id:
        stmt = stmt.where(Hotel.destination_id == destination_id)
    if min_rating is not None:
        stmt = stmt.where(Hotel.rating >= min_rating)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(stmt.offset((page - 1) * limit).limit(limit)).scalars().all()
    return paginate(items, total, page, limit, HotelOut)


@router.post("/rooms", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate, db: Session = Depends(get_db), _=Depends(require_management)):
    hotel = db.get(Hotel, payload.hotel_id)
    if not hotel or hotel.is_deleted:
        raise NotFoundError("Hotel not found")
    room = Room(**payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.get("/hotels/{hotel_id}/rooms", response_model=list[RoomOut])
def list_hotel_rooms(hotel_id: int, db: Session = Depends(get_db)):
    hotel = db.get(Hotel, hotel_id)
    if not hotel or hotel.is_deleted:
        raise NotFoundError("Hotel not found")
    stmt = select(Room).where(Room.hotel_id == hotel_id)
    return db.execute(stmt).scalars().all()


@router.post("/hotel-reservations", response_model=HotelReservationOut, status_code=status.HTTP_201_CREATED)
def create_hotel_reservation(
    payload: HotelReservationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_operations),
):
    reservation = hotel_service.create_hotel_reservation(db, payload)
    background_tasks.add_task(
        notification_service.notify_hotel_reservation_confirmation, current_user.id, reservation.id
    )
    return reservation


@router.get("/hotel-reservations", response_model=PaginatedResponse[HotelReservationOut])
def list_hotel_reservations(
    db: Session = Depends(get_db),
    booking_id: int | None = Query(None),
    room_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    _=Depends(require_operations),
):
    stmt = select(HotelReservation)
    if booking_id:
        stmt = stmt.where(HotelReservation.booking_id == booking_id)
    if room_id:
        stmt = stmt.where(HotelReservation.room_id == room_id)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(stmt.offset((page - 1) * limit).limit(limit)).scalars().all()
    return paginate(items, total, page, limit, HotelReservationOut)
