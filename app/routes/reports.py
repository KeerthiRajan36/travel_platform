import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.auth.dependencies import require_operations, require_management
from app.utils.exceptions import NotFoundError
from app.services import pdf_service, qr_service, excel_service

router = APIRouter(tags=["Bonus: PDF / QR / Excel Export"])


def _get_booking_or_404(db: Session, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError("Booking not found")
    return booking


@router.get("/bookings/{booking_id}/confirmation-pdf")
def download_booking_confirmation_pdf(
    booking_id: int, db: Session = Depends(get_db), _=Depends(require_operations)
):
    booking = _get_booking_or_404(db, booking_id)
    pdf_bytes = pdf_service.generate_booking_confirmation_pdf(booking)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="booking_{booking_id}_confirmation.pdf"'},
    )


@router.get("/bookings/{booking_id}/qr-code")
def download_booking_qr_code(booking_id: int, db: Session = Depends(get_db), _=Depends(require_operations)):
    booking = _get_booking_or_404(db, booking_id)
    png_bytes = qr_service.generate_booking_qr_png(booking)
    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="booking_{booking_id}_qr.png"'},
    )


@router.get("/dashboard/reports/export")
def export_operations_report_xlsx(db: Session = Depends(get_db), _=Depends(require_management)):
    xlsx_bytes = excel_service.generate_operations_report_xlsx(db)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="operations_report.xlsx"'},
    )
