import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class WebhookEvent(Base):
    """
    Records every webhook event we receive from Razorpay, keyed by
    Razorpay's own event_id. The unique constraint on event_id is what
    makes duplicate-webhook handling a DB guarantee, not just an
    application-level check race condition could break.
    """
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # e.g. "payment.captured"
    processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
