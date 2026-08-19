from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_customers: int
    total_packages: int
    active_tours: int
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    total_revenue: float
    total_refunds: float
    average_package_rating: float


class PopularDestination(BaseModel):
    destination_id: int
    destination_name: str
    booking_count: int


class PopularPackage(BaseModel):
    package_id: int
    package_name: str
    booking_count: int


class HotelOccupancy(BaseModel):
    hotel_id: int
    hotel_name: str
    total_rooms: int
    reserved_room_nights: int


class GuideUtilization(BaseModel):
    guide_id: int
    guide_name: str
    assignment_count: int
