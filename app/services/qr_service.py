import io

import qrcode
from qrcode.image.pil import PilImage

from app.models.booking import Booking


def _encode_payload(booking: Booking) -> str:
    return f"BOOKING-REF:{booking.id}:{booking.booking_status.value}:{float(booking.total_amount):.2f}"


def generate_booking_qr_png(booking: Booking) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(_encode_payload(booking))
    qr.make(fit=True)
    img = qr.make_image(image_factory=PilImage, fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read()
