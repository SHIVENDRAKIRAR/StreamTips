import logging

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Tip, TipStatus, WebhookEvent
from app.services.razorpay_service import verify_webhook_signature

logger = logging.getLogger("streamtips.webhooks")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    This endpoint is the ONLY place a tip can move from 'pending' to
    'success'. Nothing the client says anywhere else in the API can do
    that — see POST /tips, which only ever creates 'pending' rows.

    Order of operations matters here:
      1. Read raw bytes (signature is computed over the exact raw body —
         parsing to JSON first and re-serializing would break verification
         if key order or whitespace differs even slightly).
      2. Verify signature BEFORE trusting any content of the payload.
      3. Check idempotency (has this event_id been processed before)
         via a DB unique constraint, not just an in-memory/app check.
      4. Only then touch the tip row.
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
        # Razorpay always sends one of these; if truly absent, reject rather
        # than silently process an event we can't dedupe.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event id",
        )

    # --- Idempotency gate ---
    # Try to insert the event row first. The unique constraint on
    # event_id is the actual guarantee here: even under concurrent
    # duplicate deliveries (Razorpay does retry webhooks), only one
    # request can win this insert. The other gets IntegrityError and
    # we treat it as "already handled" — no tip mutation happens twice.
    event_row = WebhookEvent(event_id=event_id, event_type=event_type, processed=False)
    db.add(event_row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.info(f"Duplicate webhook event ignored: {event_id}")
        return {"status": "already_processed"}

    # Only handle the event type we actually care about for V1.
    if event_type != "payment.captured":
        db.commit()  # still record we saw it, just nothing to do
        return {"status": "ignored", "event_type": event_type}

    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")

    if not order_id or not payment_id:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed payment payload",
        )

    tip = db.query(Tip).filter(Tip.payment_order_id == order_id).first()
    if tip is None:
        # Event references an order we have no record of. Log and store
        # the webhook_event as processed=False evidence, but don't error
        # loudly back to Razorpay — 200 so it doesn't retry forever.
        logger.error(f"Webhook for unknown order_id: {order_id}")
        db.commit()
        return {"status": "unknown_order"}

    if tip.status == TipStatus.success:
        # Belt-and-suspenders: even if somehow two different event_ids
        # referenced the same order, don't double-apply success.
        event_row.processed = True
        db.commit()
        return {"status": "already_success"}

    tip.status = TipStatus.success
    tip.payment_id = payment_id
    event_row.processed = True
    db.commit()

    # Day 4 hook point: broadcast this tip over WebSocket to the
    # creator's overlay connection here, after commit succeeds.

    return {"status": "processed", "tip_id": str(tip.id)}
