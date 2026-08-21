from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.review import Review
from app.models.package import TourPackage
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewOut
from app.auth.dependencies import require_operations
from app.utils.exceptions import NotFoundError, ForbiddenError
from app.services import review_service

router = APIRouter(tags=["Reviews"])


@router.post("/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    customer_id: int,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    _=Depends(require_operations),
):
    
    return review_service.create_review(db, customer_id, payload)


@router.get("/packages/{package_id}/reviews", response_model=list[ReviewOut])
def list_package_reviews(package_id: int, db: Session = Depends(get_db)):
    package = db.get(TourPackage, package_id)
    if not package or package.is_deleted:
        raise NotFoundError("Tour package not found")
    stmt = select(Review).where(Review.package_id == package_id).order_by(Review.created_at.desc())
    return db.execute(stmt).scalars().all()


@router.put("/reviews/{review_id}", response_model=ReviewOut)
def update_review(review_id: int, payload: ReviewUpdate, db: Session = Depends(get_db), _=Depends(require_operations)):
    review = db.get(Review, review_id)
    if not review:
        raise NotFoundError("Review not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, db: Session = Depends(get_db), _=Depends(require_operations)):
    review = db.get(Review, review_id)
    if not review:
        raise NotFoundError("Review not found")
    db.delete(review)
    db.commit()
