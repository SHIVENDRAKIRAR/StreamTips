import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class TipCreateRequest(BaseModel):
    username: str  # which creator this tip is for
    payer_name: str = Field(min_length=1, max_length=100)
    message: str | None = Field(default=None, max_length=500)
    amount: Decimal = Field(gt=0, le=100000, decimal_places=2)  # ₹1 to ₹1,00,000, sanity cap


class TipCreateResponse(BaseModel):
    """
    Everything the frontend needs to open Razorpay Checkout.
    Note: no 'status: success' here — status only ever changes via
    the verified webhook (Day 3), never from this response.
    """
    tip_id: uuid.UUID
    razorpay_order_id: str
    razorpay_key_id: str
    amount_paise: int
    currency: str = "INR"
    creator_display_name: str


class TipPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payer_name: str
    message: str | None
    amount: Decimal
    status: str
