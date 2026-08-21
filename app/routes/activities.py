from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.package import TourPackage
from app.models.activity import Activity
from app.schemas.activity import ActivityCreate, ActivityOut
from app.schemas.common import PaginatedResponse
from app.auth.dependencies import require_management
from app.utils.exceptions import NotFoundError
from app.utils.pagination import paginate

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.post("", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db), _=Depends(require_management)):
    package = db.get(TourPackage, payload.package_id)
    if not package or package.is_deleted:
        raise NotFoundError("Tour package not found")
    activity = Activity(**payload.model_dump())
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.get("", response_model=PaginatedResponse[ActivityOut])
def list_activities(
    db: Session = Depends(get_db),
    package_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    stmt = select(Activity)
    if package_id:
        stmt = stmt.where(Activity.package_id == package_id)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(stmt.offset((page - 1) * limit).limit(limit)).scalars().all()
    return paginate(items, total, page, limit, ActivityOut)
