from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User
from app.schemas.public import CreatorPublicProfile

router = APIRouter(prefix="/creators", tags=["public"])


@router.get("/{username}", response_model=CreatorPublicProfile)
def get_creator_public_profile(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")
    return user
