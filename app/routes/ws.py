from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.booking import Booking
from app.websockets.manager import manager

router = APIRouter(tags=["Live Booking Status (WebSocket)"])


@router.websocket("/ws/bookings/{booking_id}")
async def booking_status_websocket(websocket: WebSocket, booking_id: int):

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
            
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(booking_id, websocket)
