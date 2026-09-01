import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TipStatus(str, enum.Enum):
    pending = "pending"      # order created, payment not confirmed yet
    success = "success"      # webhook verified + processed
    failed = "failed"


class Tip(Base):
    __tablename__ = "tips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Razorpay identifiers — order is created by us, payment_id comes from Razorpay on success
    payment_order_id = Column(String(100), unique=True, nullable=False, index=True)
    payment_id = Column(String(100), unique=True, nullable=True, index=True)  # null until paid

    payer_name = Column(String(100), nullable=False)
    message = Column(String(500), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)  # rupees, e.g. 500.00

    status = Column(Enum(TipStatus), default=TipStatus.pending, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
