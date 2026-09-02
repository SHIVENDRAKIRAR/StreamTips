import logging
from typing import Any

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Tip, TipStatus, WebhookEvent, User
from app.services.razorpay_service import verify_webhook_signature
from app.services.connection_manager import manager

logger = logging.getLogger("streamtips.webhooks")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

PAYMENT_CAPTURED = "payment.captured"


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    The only endpoint that can move a tip from 'pending' to 'success'.
    POST /tips never does this — it only ever creates 'pending' rows.

    Order of operations is deliberate:
      1. Read the raw request body and verify its HMAC-SHA256 signature
         before trusting any content. Signing covers the exact raw
         bytes, so parsing to JSON first and re-serializing later could
         silently break verification.
      2. Enforce idempotency via a DB unique constraint on event_id,
         not an in-memory or purely application-level check, so it
         holds up under concurrent duplicate deliveries.
      3. Only then update the tip and broadcast to the overlay.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature or not verify_webhook_signature(raw_body, signature):
        logger.warning("Rejected webhook: invalid or missing signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    payload = await request.json()
    event_id = request.headers.get("X-Razorpay-Event-Id") or payload.get("id")
    event_type = payload.get("event", "unknown")

    if not event_id:
        # Razorpay always sends one of these; if it's genuinely absent,
        # reject rather than silently process an event we can't dedupe.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event id",
        )

    if not _record_event_once(db, event_id, event_type):
        logger.info(f"Duplicate webhook event ignored: {event_id}")
        return {"status": "already_processed"}

    if event_type != PAYMENT_CAPTURED:
        db.commit()  # event recorded, nothing further to do for this type
        return {"status": "ignored", "event_type": event_type}

    order_id, payment_id = _extract_payment_ids(payload)
    if not order_id or not payment_id:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed payment payload",
        )

    tip = db.query(Tip).filter(Tip.payment_order_id == order_id).first()
    if tip is None:
        # Unknown order — log and acknowledge with 200 so Razorpay
        # doesn't retry indefinitely for an order we'll never find.
        logger.error(f"Webhook for unknown order_id: {order_id}")
        db.commit()
        return {"status": "unknown_order"}

    if tip.status == TipStatus.success:
        # Defense in depth: even if two different event_ids somehow
        # referenced the same order, never re-apply success.
        db.commit()
        return {"status": "already_success"}

    tip.status = TipStatus.success
    tip.payment_id = payment_id
    db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).update({"processed": True})
    db.commit()

    await _broadcast_tip(db, tip)

    return {"status": "processed", "tip_id": str(tip.id)}


def _record_event_once(db: Session, event_id: str, event_type: str) -> bool:
    """
    Attempts to insert a WebhookEvent row with processed=False. Returns
    False if event_id already exists (duplicate delivery), True if this
    is the first time we've seen it. The unique constraint on event_id
    is what makes this safe under concurrent requests, not this
    function alone. Callers should flip `processed` to True once the
    event has actually been acted on.
    """
    db.add(WebhookEvent(event_id=event_id, event_type=event_type, processed=False))
    try:
        db.flush()
        return True
    except IntegrityError:
        db.rollback()
        return False


def _extract_payment_ids(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Pulls order_id and payment_id out of a Razorpay payment.captured payload."""
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    return entity.get("order_id"), entity.get("id")


async def _broadcast_tip(db: Session, tip: Tip) -> None:
    """
    Pushes the tip to the creator's OBS overlay over WebSocket, if one
    is currently connected. Runs after the DB commit — the database is
    the source of truth regardless of whether anyone was watching live.
    A tip made while the overlay is offline is still recorded as
    successful; it just won't produce a live alert. There's no
    retry/queue for missed alerts in V1 — an accepted, documented cut.
    """
    creator = db.query(User).filter(User.id == tip.user_id).first()
    if creator is None:
        return

    await manager.send_to_overlay(
        creator.overlay_token,
        {
            "type": "TIP",
            "name": tip.payer_name,
            "amount": float(tip.amount),
            "message": tip.message,
        },
    )