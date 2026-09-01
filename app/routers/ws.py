import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User
from app.services.connection_manager import manager

logger = logging.getLogger("streamtips.ws")

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/overlay/{overlay_token}")
async def overlay_websocket(
    websocket: WebSocket,
    overlay_token: str,
    db: Session = Depends(get_db),
):
    """
    The OBS Browser Source connects here directly — no auth header needed
    (OBS can't send one), which is exactly why overlay_token must be a
    long random value and never derivable from username/id. Anyone who
    doesn't have this token has no way to guess it or connect as this
    creator's overlay.
    """
    # Validate the token belongs to a real creator BEFORE accepting the
    # connection, so junk/guessed tokens get a clean close, not a live
    # socket that never receives anything.
    creator = db.query(User).filter(User.overlay_token == overlay_token).first()
    if creator is None:
        await websocket.close(code=4004, reason="Invalid overlay token")
        return

    await manager.connect(overlay_token, websocket)
    try:
        while True:
            # We don't expect the client to send anything meaningful —
            # this just keeps the connection alive and lets us detect
            # disconnects promptly via the exception below. A ping/pong
            # from the browser also lands here and is safely ignored.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(overlay_token)
    except Exception:
        logger.exception(f"Unexpected error on overlay socket {overlay_token[:8]}...")
        manager.disconnect(overlay_token)
