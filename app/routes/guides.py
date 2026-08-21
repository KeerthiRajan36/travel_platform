from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.guide import TourGuide
from app.schemas.guide import GuideCreate, GuideOut, GuideAssignmentOut
from app.schemas.common import PaginatedResponse
from app.auth.dependencies import require_management
from app.utils.pagination import paginate
from app.services import guide_service

router = APIRouter(tags=["Guides"])


@router.post("/guides", response_model=GuideOut, status_code=status.HTTP_201_CREATED)
def create_guide(payload: GuideCreate, db: Session = Depends(get_db), _=Depends(require_management)):
    guide = TourGuide(**payload.model_dump())
    db.add(guide)
    db.commit()
    db.refresh(guide)
    return guide


@router.get("/guides", response_model=PaginatedResponse[GuideOut])
def list_guides(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    stmt = select(TourGuide)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(stmt.offset((page - 1) * limit).limit(limit)).scalars().all()
    return paginate(items, total, page, limit, GuideOut)


@router.post(
    "/packages/{package_id}/assign-guide/{guide_id}",
    response_model=GuideAssignmentOut,
    status_code=status.HTTP_201_CREATED,
)
def assign_guide(package_id: int, guide_id: int, db: Session = Depends(get_db), _=Depends(require_management)):
    return guide_service.assign_guide_to_package(db, package_id, guide_id)
