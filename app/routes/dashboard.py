from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.auth.dependencies import require_management
from app.schemas.dashboard import DashboardSummary, PopularDestination, PopularPackage, HotelOccupancy, GuideUtilization
from app.services import dashboard_service
from app.services.cache_service import cache_get, cache_set

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])

_SUMMARY_CACHE_KEY = "dashboard:summary"


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), _=Depends(require_management)):
    cached = cache_get(_SUMMARY_CACHE_KEY)
    if cached is not None:
        return DashboardSummary(**cached)

    result = dashboard_service.get_summary(db)
    cache_set(_SUMMARY_CACHE_KEY, result.model_dump(), ttl_seconds=settings.DASHBOARD_CACHE_TTL_SECONDS)
    return result


@router.get("/popular-destinations", response_model=list[PopularDestination])
def popular_destinations(limit: int = Query(5, ge=1, le=50), db: Session = Depends(get_db), _=Depends(require_management)):
    return dashboard_service.get_popular_destinations(db, limit)


@router.get("/popular-packages", response_model=list[PopularPackage])
def popular_packages(limit: int = Query(5, ge=1, le=50), db: Session = Depends(get_db), _=Depends(require_management)):
    return dashboard_service.get_popular_packages(db, limit)


@router.get("/hotel-occupancy", response_model=list[HotelOccupancy])
def hotel_occupancy(db: Session = Depends(get_db), _=Depends(require_management)):
    return dashboard_service.get_hotel_occupancy(db)


@router.get("/guide-utilization", response_model=list[GuideUtilization])
def guide_utilization(db: Session = Depends(get_db), _=Depends(require_management)):
    return dashboard_service.get_guide_utilization(db)


@router.get("/reports/daily-bookings")
def daily_booking_report(report_date: date = Query(default_factory=date.today), db: Session = Depends(get_db), _=Depends(require_management)):
    return dashboard_service.daily_booking_report(db, report_date)


@router.get("/reports/monthly-revenue")
def monthly_revenue_report(year: int, month: int, db: Session = Depends(get_db), _=Depends(require_management)):
    return dashboard_service.monthly_revenue_report(db, year, month)


@router.get("/reports/destination-revenue")
def destination_wise_revenue(db: Session = Depends(get_db), _=Depends(require_management)):
    return dashboard_service.destination_wise_revenue(db)


@router.get("/reports/package-performance")
def package_performance(db: Session = Depends(get_db), _=Depends(require_management)):
    return dashboard_service.package_performance_report(db)


@router.get("/reports/cancellations")
def cancellation_report(db: Session = Depends(get_db), _=Depends(require_management)):
    return dashboard_service.cancellation_report(db)


@router.get("/reports/customer-history/{customer_id}")
def customer_booking_history(customer_id: int, db: Session = Depends(get_db), _=Depends(require_management)):
    return dashboard_service.customer_booking_history(db, customer_id)
