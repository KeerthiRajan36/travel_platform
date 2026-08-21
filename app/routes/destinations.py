from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.destination import Destination, DestinationStatus
from app.schemas.destination import DestinationCreate, DestinationUpdate, DestinationOut
from app.schemas.common import PaginatedResponse
from app.auth.dependencies import require_management
from app.utils.exceptions import NotFoundError
from app.utils.pagination import paginate

router = APIRouter(prefix="/destinations", tags=["Destinations"])


@router.post("", response_model=DestinationOut, status_code=status.HTTP_201_CREATED)
def create_destination(payload: DestinationCreate, db: Session = Depends(get_db), _=Depends(require_management)):
    destination = Destination(**payload.model_dump())
    db.add(destination)
    db.commit()
    db.refresh(destination)
    return destination


@router.get("", response_model=PaginatedResponse[DestinationOut])
def list_destinations(
    db: Session = Depends(get_db),
    search: str | None = Query(None, description="Search by name or country"),
    country: str | None = Query(None),
    best_season: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    stmt = select(Destination).where(Destination.is_deleted.is_(False))
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Destination.name.ilike(like), Destination.country.ilike(like)))
    if country:
        stmt = stmt.where(Destination.country.ilike(f"%{country}%"))
    if best_season:
        stmt = stmt.where(Destination.best_season.ilike(f"%{best_season}%"))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(stmt.offset((page - 1) * limit).limit(limit)).scalars().all()
    return paginate(items, total, page, limit, DestinationOut)


@router.get("/{destination_id}", response_model=DestinationOut)
def get_destination(destination_id: int, db: Session = Depends(get_db)):
    destination = db.get(Destination, destination_id)
    if not destination or destination.is_deleted:
        raise NotFoundError("Destination not found")
    return destination


@router.put("/{destination_id}", response_model=DestinationOut)
def update_destination(
    destination_id: int, payload: DestinationUpdate, db: Session = Depends(get_db), _=Depends(require_management)
):
    destination = db.get(Destination, destination_id)
    if not destination or destination.is_deleted:
        raise NotFoundError("Destination not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(destination, field, value)
    db.add(destination)
    db.commit()
    db.refresh(destination)
    return destination


@router.delete("/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_destination(destination_id: int, db: Session = Depends(get_db), _=Depends(require_management)):
    destination = db.get(Destination, destination_id)
    if not destination or destination.is_deleted:
        raise NotFoundError("Destination not found")
    destination.is_deleted = True
    db.add(destination)
    db.commit()
