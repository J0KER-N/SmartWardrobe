from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import Dict

from ..database import get_db
from ..models import User, Garment, TryonRecord
from ..schemas import TryonCreate, TryonResponse, BaseResponse
from ..dependencies import get_current_user
from ..services.ai_clients import generate_tryon, AIClientError
from ..services.image_storage import save_tryon_image, save_image

router = APIRouter(prefix="/tryon", tags=["虚拟试穿"])

@router.post("/generate", response_model=TryonResponse)
def generate_tryon_image(
    garment_id: int = Form(...),
    user_photo: UploadFile | None = File(None),
    user_photo_url: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成虚拟试穿图片。支持 multipart/form-data 上传 `user_photo`，或传入 `user_photo_url`。"""
    # 检查衣物是否存在
    garment = db.query(Garment).filter(
        Garment.id == garment_id,
        Garment.owner_id == current_user.id,
        Garment.is_deleted == False
    ).first()
    
    if not garment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="衣物不存在"
        )
    
    try:
        # 准备 user_photo_url：优先使用上传图片，其次使用传入的 URL
        resolved_user_photo_url = None
        if user_photo is not None:
            # 将上传的用户照片保存为普通图片，并使用其 URL
            resolved_user_photo_url = save_image(user_photo, current_user.id)
        elif user_photo_url:
            resolved_user_photo_url = user_photo_url
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="必须提供 user_photo 或 user_photo_url")

        # 调用AI生成试穿图片
        tryon_result = generate_tryon(
            user_photo_url=resolved_user_photo_url,
            garment_image_url=garment.image_url
        )
        
        # 保存试穿图片
        tryon_image_url = save_tryon_image(tryon_result["image_data"], current_user.id)
        
        # 创建试穿记录
        tryon_record = TryonRecord(
            owner_id=current_user.id,
            garment_id=garment.id,
            user_photo_url=resolved_user_photo_url,
            tryon_image_url=tryon_image_url,
            tryon_status="success"
        )
        db.add(tryon_record)
        db.commit()
        db.refresh(tryon_record)
        
        return tryon_record
    
    except AIClientError as e:
        # 记录失败状态
        tryon_record = TryonRecord(
            owner_id=current_user.id,
            garment_id=garment.id,
            user_photo_url=resolved_user_photo_url,
            tryon_image_url="",
            tryon_status="failed"
        )
        db.add(tryon_record)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成试穿图片失败: {str(e)}"
        )

@router.get("/records/{record_id}", response_model=TryonResponse)
def get_tryon_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取试穿记录"""
    record = db.query(TryonRecord).filter(
        TryonRecord.id == record_id,
        TryonRecord.owner_id == current_user.id
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="试穿记录不存在"
        )
    
    return record