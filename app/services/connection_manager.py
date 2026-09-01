import logging

from fastapi import WebSocket

logger = logging.getLogger("streamtips.ws")


class ConnectionManager:
    """
    Maps overlay_token -> the live WebSocket connection for that creator's
    OBS overlay. Single-process, in-memory — deliberate V1 scope cut.

    If this were horizontally scaled across multiple server instances,
    a client connected to instance A wouldn't receive events broadcast
    from instance B. That's exactly the case for introducing Redis
    Pub/Sub (or another broker) later — not needed at V1 scale.

    Using a dict of one connection per token (not a list) is intentional:
    a creator only has one OBS overlay open at a time in practice. If a
    second connection comes in for the same token (e.g. reconnect before
    the old one timed out), it replaces the old one.
    """

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, overlay_token: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[overlay_token] = websocket
        logger.info(f"Overlay connected: {overlay_token[:8]}...")

    def disconnect(self, overlay_token: str) -> None:
        self._connections.pop(overlay_token, None)
        logger.info(f"Overlay disconnected: {overlay_token[:8]}...")

    async def send_to_overlay(self, overlay_token: str, message: dict) -> bool:
        """
        Returns True if a live connection existed and the send succeeded,
        False otherwise (no overlay currently connected, or send failed —
        e.g. OBS was closed without a clean disconnect). Caller doesn't
        need to treat False as an error: it just means nobody was
        watching live, which is a normal/expected state, not a bug.
        """
        websocket = self._connections.get(overlay_token)
        if websocket is None:
            return False
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            logger.warning(f"Failed to send to overlay {overlay_token[:8]}..., dropping connection")
            self.disconnect(overlay_token)
            return False


manager = ConnectionManager()
