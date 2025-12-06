from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..dependencies import get_current_user, get_db
from ..models import User
from ..security import get_password_hash

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=schemas.UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("", response_model=schemas.UserOut)
def update_profile(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.dict(exclude_unset=True)
    password = data.pop("password", None)
    for field, value in data.items():
        setattr(current_user, field, value)
    if password:
        current_user.hashed_password = get_password_hash(password)
    db.commit()
    db.refresh(current_user)
    return current_user

