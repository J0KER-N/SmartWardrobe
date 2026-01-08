from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
import logging
from sqlalchemy.orm import Session
from typing import Dict

from ..database import get_db
from ..models import User, Garment, TryonRecord
from ..schemas import TryonCreate, TryonResponse, BaseResponse
from ..dependencies import get_current_user
from ..services.ai_clients import generate_tryon, AIClientError
from ..services.image_storage import save_tryon_image, save_tryon_user_photo, validate_tryon_image

router = APIRouter(prefix="/tryon", tags=["虚拟试穿"])
logger = logging.getLogger(__name__)

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
            # 保存试衣用户照片（使用更大的大小限制，20MB）
            resolved_user_photo_url = save_tryon_user_photo(user_photo, current_user.id)
        elif user_photo_url:
            resolved_user_photo_url = user_photo_url
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="必须提供 user_photo 或 user_photo_url")

        # 调用AI生成试穿图片
        tryon_result = generate_tryon(
            user_photo_url=resolved_user_photo_url,
            garment_image_url=garment.image_url
        )
        
        # 保存试穿图片（捕获并记录保存失败的详细异常）
        try:
            tryon_image_url = save_tryon_image(tryon_result["image_data"], current_user.id)
        except Exception as e:
            logger.exception("保存试穿图片失败（user_id=%s, garment_id=%s）", current_user.id, garment.id)
            # 记录失败状态到数据库
            tryon_record = TryonRecord(
                owner_id=current_user.id,
                garment_id=garment.id,
                user_photo_url=resolved_user_photo_url,
                tryon_image_url="",
                tryon_status="failed"
            )
            db.add(tryon_record)
            db.commit()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="试穿图片保存失败")
        
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
        # 记录失败状态和详细错误信息
        error_detail = str(e)
        logger.error(f"生成试穿图片失败（user_id={current_user.id}, garment_id={garment.id}）: {error_detail}")
        
        tryon_record = TryonRecord(
            owner_id=current_user.id,
            garment_id=garment.id,
            user_photo_url=resolved_user_photo_url,
            tryon_image_url="",
            tryon_status="failed"
        )
        db.add(tryon_record)
        db.commit()
        
        # 根据错误类型返回不同的状态码和消息
        if "超时" in error_detail or "timeout" in error_detail.lower():
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"生成试穿图片超时，请稍后重试。错误详情: {error_detail}"
            )
        elif "限流" in error_detail or "rate limit" in error_detail.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请稍后重试。错误详情: {error_detail}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"生成试穿图片失败: {error_detail}"
            )
    except Exception as e:
        # 捕获其他未预期的异常
        logger.exception(f"生成试穿图片时发生未预期的异常（user_id={current_user.id}, garment_id={garment.id}）")
        
        tryon_record = TryonRecord(
            owner_id=current_user.id,
            garment_id=garment.id,
            user_photo_url=resolved_user_photo_url if 'resolved_user_photo_url' in locals() else "",
            tryon_image_url="",
            tryon_status="failed"
        )
        db.add(tryon_record)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成试穿图片时发生错误: {str(e)}"
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