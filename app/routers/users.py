from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.user import UserPublic, UserProfileUpdate, OverlayInfo

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserPublic)
def update_my_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/overlay", response_model=OverlayInfo)
def get_my_overlay_info(current_user: User = Depends(get_current_user)):
    """
    Returns the creator's private overlay URL/token — only ever visible
    to the authenticated creator themself. This is what they paste into
    OBS Browser Source. Never expose this on a public profile endpoint.
    """
    return OverlayInfo(
        overlay_token=current_user.overlay_token,
        overlay_url_path=f"/overlay/{current_user.overlay_token}",
    )
