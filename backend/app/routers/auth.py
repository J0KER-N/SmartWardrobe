from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import schemas
from ..config import get_settings
from ..dependencies import get_db
from ..models import User
from ..security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    validate_password,
    validate_phone,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=schemas.UserOut)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    # Validate phone number
    if not validate_phone(user_in.phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format. Must be 11 digits starting with 1",
        )

    # Check if phone already registered
    if db.query(User).filter(User.phone == user_in.phone).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone already registered")

    # Validate password strength
    is_valid, error_msg = validate_password(user_in.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # Validate nickname length
    if user_in.nickname and len(user_in.nickname) > 64:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nickname too long (max 64 characters)")

    user = User(
        phone=user_in.phone,
        nickname=user_in.nickname or f"衣橱用户{user_in.phone[-4:]}",
        hashed_password=get_password_hash(user_in.password),
        location=user_in.location,
        gender=user_in.gender,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Validate phone format
    if not validate_phone(form_data.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number format")

    user = db.query(User).filter(User.phone == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password",
        )

    access_token = create_access_token(subject=user.phone)
    refresh_token = create_refresh_token(subject=user.phone)

    return schemas.Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=schemas.Token)
def refresh_token(payload: schemas.TokenRefresh, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    from ..security import decode_token

    try:
        token_payload = decode_token(payload.refresh_token, token_type="refresh")
        user = db.query(User).filter(User.phone == token_payload.sub).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        new_access_token = create_access_token(subject=user.phone)
        new_refresh_token = create_refresh_token(subject=user.phone)

        return schemas.Token(access_token=new_access_token, refresh_token=new_refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

