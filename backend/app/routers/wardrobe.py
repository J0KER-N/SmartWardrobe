from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from .. import schemas
from ..config import get_settings
from ..dependencies import get_current_user, get_db
from ..models import Garment, GarmentTag, User
from ..services import tagging
from ..services.image_storage import build_public_url, save_temp_image

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])
settings = get_settings()


@router.get("/items", response_model=List[schemas.GarmentOut])
def list_garments(
    category: Optional[str] = None,
    scene: Optional[str] = None,
    style: Optional[str] = None,
    season: Optional[str] = None,
    colorway: Optional[str] = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(None, ge=1, le=settings.max_page_size, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List garments with filtering and pagination."""
    page_size = page_size or settings.default_page_size
    offset = (page - 1) * page_size

    query = db.query(Garment).filter(Garment.owner_id == current_user.id, Garment.is_deleted.is_(False))
    if category:
        query = query.filter(Garment.category == category)
    if scene:
        query = query.filter(Garment.scene == scene)
    if style:
        query = query.filter(Garment.style == style)
    if season:
        query = query.filter(Garment.season == season)
    if colorway:
        query = query.filter(Garment.colorway == colorway)

    return query.order_by(Garment.created_at.desc()).offset(offset).limit(page_size).all()


@router.post("/items", response_model=schemas.GarmentOut)
async def create_garment(
    name: str = Form(..., min_length=1, max_length=120),
    category: str = Form(..., min_length=1, max_length=64),
    scene: Optional[str] = Form(None, max_length=64),
    style: Optional[str] = Form(None, max_length=64),
    season: Optional[str] = Form(None, max_length=32),
    colorway: Optional[str] = Form(None, max_length=32),
    price: Optional[int] = Form(None, ge=0),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    auto_tags = {}
    image_url = None
    if image:
        # Validate image format
        from ..services.image_storage import validate_image_format, validate_image_size

        validate_image_format(image.filename or "")
        content = await image.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty image upload")
        validate_image_size(content)

        # Auto-tag with AI
        try:
            auto_tags = await tagging.auto_tag_image(content)
        except Exception as e:
            # Log error but continue without auto-tags
            import logging
            logging.getLogger(__name__).warning(f"Failed to auto-tag image: {str(e)}")

        # Save image
        suffix = f".{image.filename.split('.')[-1]}" if "." in (image.filename or "") else ".jpg"
        path = save_temp_image(content, suffix=suffix, compress=True)
        image_url = build_public_url(path)

    garment = Garment(
        owner_id=current_user.id,
        name=name,
        category=category or auto_tags.get("category"),
        scene=scene or auto_tags.get("scene"),
        style=style or auto_tags.get("style"),
        season=season or auto_tags.get("season"),
        colorway=colorway or auto_tags.get("colorway"),
        image_url=image_url,
        extra_tags=auto_tags.get("extra"),
    )
    db.add(garment)
    db.commit()
    db.refresh(garment)
    return garment


@router.put("/items/{garment_id}", response_model=schemas.GarmentOut)
def update_garment(
    garment_id: int,
    payload: schemas.GarmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    garment = (
        db.query(Garment)
        .filter(Garment.id == garment_id, Garment.owner_id == current_user.id, Garment.is_deleted.is_(False))
        .first()
    )
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(garment, field, value)
    db.commit()
    db.refresh(garment)
    return garment


@router.delete("/items/{garment_id}")
def delete_garment(
    garment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    garment = db.query(Garment).filter(Garment.id == garment_id, Garment.owner_id == current_user.id).first()
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")
    garment.is_deleted = True
    db.commit()
    return {"status": "deleted"}

