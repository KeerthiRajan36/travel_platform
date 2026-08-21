from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.booking import Booking
from app.websockets.manager import manager

router = APIRouter(tags=["Live Booking Status (WebSocket)"])


@router.websocket("/ws/bookings/{booking_id}")
async def booking_status_websocket(websocket: WebSocket, booking_id: int):
    """Live booking status feed.

    Connect with any WebSocket client, e.g.:
        wscat -c ws://localhost:8000/ws/bookings/1

    On connect, immediately sends the booking's current status. After that,
    it pushes a message every time the booking's status changes (payment
    confirms it, it gets cancelled, etc.) via the connection manager.
    """
    await manager.connect(booking_id, websocket)

    db: Session = SessionLocal()
    try:
        booking = db.get(Booking, booking_id)
        if booking is None:
            await websocket.send_json({"error": f"Booking {booking_id} not found"})
        else:
            await websocket.send_json({"booking_id": booking_id, "status": booking.booking_status.value})
    finally:
        db.close()

    try:
        while True:
            # This endpoint is push-only; we just keep the socket open and
            # discard anything the client sends (e.g. ping frames).
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(booking_id, websocket)
