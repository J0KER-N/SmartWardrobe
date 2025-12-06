from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..config import get_settings
from ..dependencies import get_current_user, get_db
from ..models import FavoriteLook, TryOnRecord, User

router = APIRouter(prefix="/records", tags=["records"])
settings = get_settings()


@router.get("/history", response_model=List[schemas.TryOnResponse])
def list_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(None, ge=1, le=settings.max_page_size, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List try-on history with pagination."""
    page_size = page_size or settings.default_page_size
    offset = (page - 1) * page_size

    records = (
        db.query(TryOnRecord)
        .filter(TryOnRecord.user_id == current_user.id)
        .order_by(TryOnRecord.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return [
        schemas.TryOnResponse(
            record_id=r.id,
            status=r.status.value,
            result_image_url=r.result_image_url,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.get("/history/count")
def get_history_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get total count of try-on records."""
    count = db.query(TryOnRecord).filter(TryOnRecord.user_id == current_user.id).count()
    return {"total": count}


@router.post("/favorites", response_model=schemas.FavoriteOut)
def add_favorite(payload: schemas.FavoriteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(TryOnRecord).filter(TryOnRecord.id == payload.record_id, TryOnRecord.user_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    favorite = FavoriteLook(user_id=current_user.id, record_id=record.id, notes=payload.notes)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


@router.get("/favorites", response_model=List[schemas.FavoriteOut])
def list_favorites(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(None, ge=1, le=settings.max_page_size, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List favorite looks with pagination."""
    page_size = page_size or settings.default_page_size
    offset = (page - 1) * page_size

    return (
        db.query(FavoriteLook)
        .filter(FavoriteLook.user_id == current_user.id)
        .order_by(FavoriteLook.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

