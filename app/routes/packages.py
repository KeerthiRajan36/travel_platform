from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.package import TourPackage, PackageStatus
from app.models.destination import Destination
from app.models.review import Review
from app.schemas.package import PackageCreate, PackageUpdate, PackageOut
from app.schemas.common import PaginatedResponse
from app.auth.dependencies import require_management
from app.utils.exceptions import NotFoundError, BadRequestError
from app.utils.pagination import paginate

router = APIRouter(prefix="/packages", tags=["Tour Packages"])


@router.post("", response_model=PackageOut, status_code=status.HTTP_201_CREATED)
def create_package(payload: PackageCreate, db: Session = Depends(get_db), _=Depends(require_management)):
    destination = db.get(Destination, payload.destination_id)
    if not destination or destination.is_deleted:
        raise NotFoundError("Destination not found")

    data = payload.model_dump()
    # available_slots starts out equal to max_capacity and can never exceed it.
    package = TourPackage(**data, available_slots=data["max_capacity"])
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@router.get("", response_model=PaginatedResponse[PackageOut])
def list_packages(
    db: Session = Depends(get_db),
    destination_id: int | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    min_duration: int | None = Query(None, ge=0),
    max_duration: int | None = Query(None, ge=0),
    start_after: date | None = Query(None),
    start_before: date | None = Query(None),
    only_available: bool = Query(False, description="Only packages with available_slots > 0"),
    min_rating: float | None = Query(None, ge=1, le=5),
    status_filter: PackageStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
):
    stmt = select(TourPackage).where(TourPackage.is_deleted.is_(False))

    if destination_id:
        stmt = stmt.where(TourPackage.destination_id == destination_id)
    if min_price is not None:
        stmt = stmt.where(TourPackage.base_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(TourPackage.base_price <= max_price)
    if min_duration is not None:
        stmt = stmt.where(TourPackage.duration_days >= min_duration)
    if max_duration is not None:
        stmt = stmt.where(TourPackage.duration_days <= max_duration)
    if start_after is not None:
        stmt = stmt.where(TourPackage.start_date >= start_after)
    if start_before is not None:
        stmt = stmt.where(TourPackage.start_date <= start_before)
    if only_available:
        stmt = stmt.where(TourPackage.available_slots > 0)
    if status_filter is not None:
        stmt = stmt.where(TourPackage.status == status_filter)
    if min_rating is not None:
        rated_ids = select(Review.package_id).group_by(Review.package_id).having(func.avg(Review.rating) >= min_rating)
        stmt = stmt.where(TourPackage.id.in_(rated_ids))

    sort_column = getattr(TourPackage, sort_by, TourPackage.id)
    stmt = stmt.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(stmt.offset((page - 1) * limit).limit(limit)).scalars().all()
    return paginate(items, total, page, limit, PackageOut)


@router.get("/{package_id}", response_model=PackageOut)
def get_package(package_id: int, db: Session = Depends(get_db)):
    package = db.get(TourPackage, package_id)
    if not package or package.is_deleted:
        raise NotFoundError("Tour package not found")
    return package


@router.put("/{package_id}", response_model=PackageOut)
def update_package(
    package_id: int, payload: PackageUpdate, db: Session = Depends(get_db), _=Depends(require_management)
):
    package = db.get(TourPackage, package_id)
    if not package or package.is_deleted:
        raise NotFoundError("Tour package not found")

    data = payload.model_dump(exclude_unset=True)

    new_start = data.get("start_date", package.start_date)
    new_end = data.get("end_date", package.end_date)
    if new_end <= new_start:
        raise BadRequestError("end_date must be after start_date")

    if "max_capacity" in data:
        already_used = package.max_capacity - package.available_slots
        if data["max_capacity"] < already_used:
            raise BadRequestError("max_capacity cannot be lower than already booked slots")
        package.available_slots = data["max_capacity"] - already_used

    for field, value in data.items():
        setattr(package, field, value)

    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(package_id: int, db: Session = Depends(get_db), _=Depends(require_management)):
    package = db.get(TourPackage, package_id)
    if not package or package.is_deleted:
        raise NotFoundError("Tour package not found")
    package.is_deleted = True
    db.add(package)
    db.commit()
