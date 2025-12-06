import base64

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from .. import schemas
from ..dependencies import get_current_user, get_db
from ..models import Garment, TryOnRecord, TryOnStatus, User
from ..services import ai_clients
from ..services.image_storage import build_public_url, save_temp_image

router = APIRouter(prefix="/tryon", tags=["try-on"])


@router.post("/generate", response_model=schemas.TryOnResponse)
async def generate_tryon(
    payload: schemas.TryOnRequest,
    user_photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    garments = (
        db.query(Garment)
        .filter(Garment.id.in_(payload.garment_ids), Garment.owner_id == current_user.id, Garment.is_deleted.is_(False))
        .all()
    )
    if len(garments) != len(payload.garment_ids):
        raise HTTPException(status_code=404, detail="Some garments not found")

    user_image_bytes = await user_photo.read()
    if not user_image_bytes:
        raise HTTPException(status_code=400, detail="Empty user image")

    garment_images = []
    for garment in garments:
        if not garment.image_url:
            raise HTTPException(status_code=400, detail=f"Garment {garment.id} missing image")
        with open(garment.image_url, "rb") as fh:
            garment_images.append(base64.b64encode(fh.read()).decode("utf-8"))

    record = TryOnRecord(user_id=current_user.id, garment_ids=payload.garment_ids, status=TryOnStatus.pending)
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        result_b64 = await ai_clients.generate_tryon(
            user_image_b64=base64.b64encode(user_image_bytes).decode("utf-8"),
            garment_images=garment_images,
            prompt=payload.prompt,
        )
        image_bytes = base64.b64decode(result_b64)
        path = save_temp_image(image_bytes, suffix=".png")
        record.result_image_url = build_public_url(path)
        record.status = TryOnStatus.completed
    except Exception as exc:
        record.status = TryOnStatus.failed
        record.meta_data = {"error": str(exc)}
        db.commit()
        raise HTTPException(status_code=500, detail="Try-on generation failed") from exc

    db.commit()
    db.refresh(record)
    return schemas.TryOnResponse(
        record_id=record.id,
        status=record.status.value,
        result_image_url=record.result_image_url,
        created_at=record.created_at,
    )

