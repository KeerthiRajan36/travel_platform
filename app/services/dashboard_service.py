from datetime import date

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.package import TourPackage, PackageStatus
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.models.review import Review
from app.models.destination import Destination
from app.models.hotel import Hotel
from app.models.room import Room
from app.models.hotel_reservation import HotelReservation
from app.models.guide import TourGuide, GuideAssignment
from app.schemas.dashboard import (
    DashboardSummary, PopularDestination, PopularPackage, HotelOccupancy, GuideUtilization,
)


def get_summary(db: Session) -> DashboardSummary:
    total_customers = db.execute(select(func.count()).select_from(Customer).where(Customer.is_deleted.is_(False))).scalar_one()
    total_packages = db.execute(select(func.count()).select_from(TourPackage).where(TourPackage.is_deleted.is_(False))).scalar_one()
    active_tours = db.execute(
        select(func.count()).select_from(TourPackage).where(
            TourPackage.status.in_([PackageStatus.PUBLISHED, PackageStatus.FULL]),
            TourPackage.is_deleted.is_(False),
        )
    ).scalar_one()
    total_bookings = db.execute(select(func.count()).select_from(Booking).where(Booking.is_deleted.is_(False))).scalar_one()
    confirmed_bookings = db.execute(
        select(func.count()).select_from(Booking).where(Booking.booking_status == BookingStatus.CONFIRMED)
    ).scalar_one()
    cancelled_bookings = db.execute(
        select(func.count()).select_from(Booking).where(Booking.booking_status == BookingStatus.CANCELLED)
    ).scalar_one()
    total_revenue = db.execute(
        select(func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)).where(
            Payment.payment_status.in_([PaymentStatus.SUCCESS, PaymentStatus.REFUNDED])
        )
    ).scalar_one()
    total_refunds = db.execute(select(func.coalesce(func.sum(Payment.refunded_amount), 0))).scalar_one()
    avg_rating = db.execute(select(func.coalesce(func.avg(Review.rating), 0))).scalar_one()

    return DashboardSummary(
        total_customers=total_customers,
        total_packages=total_packages,
        active_tours=active_tours,
        total_bookings=total_bookings,
        confirmed_bookings=confirmed_bookings,
        cancelled_bookings=cancelled_bookings,
        total_revenue=float(total_revenue),
        total_refunds=float(total_refunds),
        average_package_rating=round(float(avg_rating), 2),
    )


def get_popular_destinations(db: Session, limit: int = 5) -> list[PopularDestination]:
    stmt = (
        select(Destination.id, Destination.name, func.count(Booking.id).label("cnt"))
        .join(TourPackage, TourPackage.destination_id == Destination.id)
        .join(Booking, Booking.package_id == TourPackage.id)
        .where(Booking.booking_status != BookingStatus.CANCELLED)
        .group_by(Destination.id, Destination.name)
        .order_by(func.count(Booking.id).desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [PopularDestination(destination_id=r[0], destination_name=r[1], booking_count=r[2]) for r in rows]


def get_popular_packages(db: Session, limit: int = 5) -> list[PopularPackage]:
    stmt = (
        select(TourPackage.id, TourPackage.package_name, func.count(Booking.id).label("cnt"))
        .join(Booking, Booking.package_id == TourPackage.id)
        .where(Booking.booking_status != BookingStatus.CANCELLED)
        .group_by(TourPackage.id, TourPackage.package_name)
        .order_by(func.count(Booking.id).desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [PopularPackage(package_id=r[0], package_name=r[1], booking_count=r[2]) for r in rows]


def get_hotel_occupancy(db: Session) -> list[HotelOccupancy]:
    hotels = db.execute(select(Hotel).where(Hotel.is_deleted.is_(False))).scalars().all()
    result = []
    for hotel in hotels:
        total_rooms = db.execute(select(func.count()).select_from(Room).where(Room.hotel_id == hotel.id)).scalar_one()
        reserved_nights = db.execute(
            select(func.coalesce(func.sum(func.julianday(HotelReservation.check_out) - func.julianday(HotelReservation.check_in)), 0))
            .join(Room, Room.id == HotelReservation.room_id)
            .where(Room.hotel_id == hotel.id)
        ).scalar_one()
        result.append(
            HotelOccupancy(
                hotel_id=hotel.id,
                hotel_name=hotel.hotel_name,
                total_rooms=total_rooms,
                reserved_room_nights=int(reserved_nights or 0),
            )
        )
    return result


def get_guide_utilization(db: Session) -> list[GuideUtilization]:
    stmt = (
        select(TourGuide.id, TourGuide.name, func.count(GuideAssignment.id).label("cnt"))
        .outerjoin(GuideAssignment, GuideAssignment.guide_id == TourGuide.id)
        .group_by(TourGuide.id, TourGuide.name)
        .order_by(func.count(GuideAssignment.id).desc())
    )
    rows = db.execute(stmt).all()
    return [GuideUtilization(guide_id=r[0], guide_name=r[1], assignment_count=r[2]) for r in rows]


def daily_booking_report(db: Session, day: date) -> dict:
    stmt = select(func.count(), func.coalesce(func.sum(Booking.total_amount), 0)).where(
        func.date(Booking.booking_date) == day.isoformat()
    )
    count, revenue = db.execute(stmt).one()
    return {"date": day.isoformat(), "bookings": count, "revenue": float(revenue)}


def monthly_revenue_report(db: Session, year: int, month: int) -> dict:
    stmt = select(func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)).where(
        func.strftime("%Y", Payment.payment_date) == f"{year:04d}",
        func.strftime("%m", Payment.payment_date) == f"{month:02d}",
        Payment.payment_status.in_([PaymentStatus.SUCCESS, PaymentStatus.REFUNDED]),
    )
    revenue = db.execute(stmt).scalar_one()
    return {"year": year, "month": month, "revenue": float(revenue)}


def destination_wise_revenue(db: Session) -> list[dict]:
    stmt = (
        select(Destination.id, Destination.name, func.coalesce(func.sum(Booking.total_amount), 0))
        .join(TourPackage, TourPackage.destination_id == Destination.id)
        .join(Booking, Booking.package_id == TourPackage.id)
        .where(Booking.booking_status != BookingStatus.CANCELLED)
        .group_by(Destination.id, Destination.name)
        .order_by(func.sum(Booking.total_amount).desc())
    )
    rows = db.execute(stmt).all()
    return [{"destination_id": r[0], "destination_name": r[1], "revenue": float(r[2])} for r in rows]


def package_performance_report(db: Session) -> list[dict]:
    stmt = (
        select(
            TourPackage.id,
            TourPackage.package_name,
            func.count(Booking.id),
            func.coalesce(func.sum(Booking.total_amount), 0),
        )
        .outerjoin(Booking, Booking.package_id == TourPackage.id)
        .where(TourPackage.is_deleted.is_(False))
        .group_by(TourPackage.id, TourPackage.package_name)
    )
    rows = db.execute(stmt).all()
    return [
        {"package_id": r[0], "package_name": r[1], "total_bookings": r[2], "total_revenue": float(r[3])}
        for r in rows
    ]


def cancellation_report(db: Session) -> dict:
    from app.models.cancellation import Cancellation

    stmt = select(func.count(), func.coalesce(func.sum(Cancellation.refund_amount), 0))
    count, refunded = db.execute(stmt).one()
    return {"total_cancellations": count, "total_refunded": float(refunded)}


def customer_booking_history(db: Session, customer_id: int) -> list[dict]:
    stmt = select(Booking).where(Booking.customer_id == customer_id).order_by(Booking.booking_date.desc())
    bookings = db.execute(stmt).scalars().all()
    return [
        {
            "booking_id": b.id,
            "package_id": b.package_id,
            "booking_date": b.booking_date.isoformat(),
            "status": b.booking_status.value,
            "total_amount": float(b.total_amount),
        }
        for b in bookings
    ]
