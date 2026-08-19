from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.guide import TourGuide, GuideAssignment, GuideAvailability
from app.models.package import TourPackage
from app.utils.exceptions import NotFoundError, BadRequestError, ConflictError


def assign_guide_to_package(db: Session, package_id: int, guide_id: int) -> GuideAssignment:
    package = db.get(TourPackage, package_id)
    if not package or package.is_deleted:
        raise NotFoundError("Tour package not found")

    guide = db.get(TourGuide, guide_id)
    if not guide:
        raise NotFoundError("Tour guide not found")

    if guide.availability_status == GuideAvailability.INACTIVE:
        raise BadRequestError("Inactive guides cannot be assigned")

    # Overlap check: guide cannot be assigned to two tours whose date
    # ranges intersect.
    overlap = db.execute(
        select(GuideAssignment).where(
            and_(
                GuideAssignment.guide_id == guide_id,
                GuideAssignment.start_date <= package.end_date,
                GuideAssignment.end_date >= package.start_date,
            )
        )
    ).scalar_one_or_none()
    if overlap:
        raise ConflictError("Guide is already assigned to an overlapping tour")

    assignment = GuideAssignment(
        package_id=package_id,
        guide_id=guide_id,
        start_date=package.start_date,
        end_date=package.end_date,
    )
    db.add(assignment)
    guide.availability_status = GuideAvailability.UNAVAILABLE
    db.add(guide)
    db.commit()
    db.refresh(assignment)
    return assignment
