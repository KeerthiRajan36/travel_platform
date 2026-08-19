import io

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER

from app.models.booking import Booking
from app.services.qr_service import generate_booking_qr_png


def generate_booking_confirmation_pdf(booking: Booking) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCentered", parent=styles["Title"], alignment=TA_CENTER)

    story = []

    story.append(Paragraph("Booking Confirmation", title_style))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Travel &amp; Tour Operations Management Platform", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))

    package = booking.package
    customer = booking.customer

    details = [
        ["Booking ID", f"#{booking.id}"],
        ["Status", booking.booking_status.value],
        ["Customer", customer.name],
        ["Customer Email", customer.email],
        ["Package", package.package_name],
        ["Destination", package.destination.name],
        ["Travel Dates", f"{package.start_date.isoformat()} to {package.end_date.isoformat()}"],
        ["Number of Travelers", str(booking.number_of_travelers)],
        ["Base Amount", f"{float(booking.base_amount):.2f}"],
        ["Discount", f"-{float(booking.discount):.2f}"],
        ["Tax", f"+{float(booking.tax):.2f}"],
        ["Total Amount", f"{float(booking.total_amount):.2f}"],
    ]
    table = Table(details, colWidths=[60 * mm, 100 * mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.lightgrey),
        ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
    ]))
    story.append(table)
    story.append(Spacer(1, 10 * mm))

    story.append(Paragraph("Scan to verify this booking:", styles["Normal"]))
    story.append(Spacer(1, 3 * mm))
    qr_bytes = generate_booking_qr_png(booking)
    story.append(Image(io.BytesIO(qr_bytes), width=35 * mm, height=35 * mm))

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "This is an automatically generated confirmation. Please retain it for your records.",
        styles["Italic"],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
