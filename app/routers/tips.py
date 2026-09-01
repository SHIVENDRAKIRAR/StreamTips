import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import User, Tip, TipStatus
from app.schemas.tip import TipCreateRequest, TipCreateResponse
from app.services.razorpay_service import create_razorpay_order

router = APIRouter(prefix="/tips", tags=["tips"])


@router.post("", response_model=TipCreateResponse, status_code=status.HTTP_201_CREATED)
def create_tip(payload: TipCreateRequest, db: Session = Depends(get_db)):
    creator = db.query(User).filter(User.username == payload.username).first()
    if creator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")

    # Receipt id must be unique per order — use a fresh uuid, not user-controlled input
    receipt = f"tip_{uuid.uuid4().hex[:20]}"

    order = create_razorpay_order(amount_rupees=float(payload.amount), receipt=receipt)

    # IMPORTANT: this tip row is created as 'pending'. It only ever becomes
    # 'success' via the verified webhook in Day 3 — never from this request,
    # and never from anything the client tells us after this point.
    tip = Tip(
        user_id=creator.id,
        payment_order_id=order["id"],
        payer_name=payload.payer_name,
        message=payload.message,
        amount=payload.amount,
        status=TipStatus.pending,
    )
    db.add(tip)
    db.commit()
    db.refresh(tip)

    return TipCreateResponse(
        tip_id=tip.id,
        razorpay_order_id=order["id"],
        razorpay_key_id=settings.RAZORPAY_KEY_ID,
        amount_paise=order["amount"],
        creator_display_name=creator.display_name,
    )
