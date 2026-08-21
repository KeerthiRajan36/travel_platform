from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerOut
from app.schemas.common import PaginatedResponse
from app.auth.dependencies import require_operations
from app.utils.exceptions import NotFoundError, ConflictError
from app.utils.pagination import paginate

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), _=Depends(require_operations)):
    existing = db.execute(select(Customer).where(Customer.email == payload.email)).scalar_one_or_none()
    if existing:
        raise ConflictError("A customer with this email already exists")
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("", response_model=PaginatedResponse[CustomerOut])
def list_customers(
    db: Session = Depends(get_db),
    name: str | None = Query(None),
    email: str | None = Query(None),
    phone: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    _=Depends(require_operations),
):
    stmt = select(Customer).where(Customer.is_deleted.is_(False))
    if name:
        stmt = stmt.where(Customer.name.ilike(f"%{name}%"))
    if email:
        stmt = stmt.where(Customer.email.ilike(f"%{email}%"))
    if phone:
        stmt = stmt.where(Customer.phone.ilike(f"%{phone}%"))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(stmt.offset((page - 1) * limit).limit(limit)).scalars().all()
    return paginate(items, total, page, limit, CustomerOut)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db), _=Depends(require_operations)):
    customer = db.get(Customer, customer_id)
    if not customer or customer.is_deleted:
        raise NotFoundError("Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db), _=Depends(require_operations)
):
    customer = db.get(Customer, customer_id)
    if not customer or customer.is_deleted:
        raise NotFoundError("Customer not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer
