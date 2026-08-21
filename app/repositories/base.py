from typing import Generic, TypeVar, Type, Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """Generic repository providing basic CRUD + pagination for a model.

    Entity-specific repositories can subclass this and add custom queries
    (filters, joins, aggregate reports, etc.) on top.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model
        self.has_soft_delete = hasattr(model, "is_deleted")

    def _base_query(self):
        stmt = select(self.model)
        if self.has_soft_delete:
            stmt = stmt.where(self.model.is_deleted.is_(False))
        return stmt

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        stmt = self._base_query().where(self.model.id == id)
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(
        self, db: Session, skip: int = 0, limit: int = 10, order_by=None
    ) -> Sequence[ModelType]:
        stmt = self._base_query()
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(skip).limit(limit)
        return db.execute(stmt).scalars().all()

    def count(self, db: Session) -> int:
        stmt = select(func.count()).select_from(self.model)
        if self.has_soft_delete:
            stmt = stmt.where(self.model.is_deleted.is_(False))
        return db.execute(stmt).scalar_one()

    def create(self, db: Session, obj_in: dict) -> ModelType:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: ModelType, obj_in: dict) -> ModelType:
        for field, value in obj_in.items():
            if value is not None:
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, db_obj: ModelType, soft: bool = True) -> None:
        if soft and self.has_soft_delete:
            db_obj.is_deleted = True
            db.add(db_obj)
            db.commit()
        else:
            db.delete(db_obj)
            db.commit()
