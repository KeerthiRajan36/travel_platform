import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger("websockets")


class BookingStatusConnectionManager:
    def __init__(self):
        self._active: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, booking_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._active[booking_id].append(websocket)

    def disconnect(self, booking_id: int, websocket: WebSocket) -> None:
        if websocket in self._active.get(booking_id, []):
            self._active[booking_id].remove(websocket)
        if not self._active.get(booking_id):
            self._active.pop(booking_id, None)

    async def broadcast(self, booking_id: int, message: dict) -> None:
        connections = list(self._active.get(booking_id, []))
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception as exc:  # noqa: BLE001
                logger.info("Dropping dead websocket for booking %s: %s", booking_id, exc)
                self.disconnect(booking_id, ws)


manager = BookingStatusConnectionManager()


async def broadcast_booking_status(booking_id: int, status: str, extra: dict | None = None) -> None:
    message = {"booking_id": booking_id, "status": status}
    if extra:
        message.update(extra)
    await manager.broadcast(booking_id, message)
