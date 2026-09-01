import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def generate_overlay_token() -> str:
    """
    A random, non-guessable token used in the OBS overlay URL.
    This is what stops someone from finding/spoofing another
    creator's overlay stream. Never derived from username/id.
    """
    return uuid.uuid4().hex + uuid.uuid4().hex  # 64 hex chars


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False)
    overlay_token = Column(
        String(128), unique=True, nullable=False, default=generate_overlay_token
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
