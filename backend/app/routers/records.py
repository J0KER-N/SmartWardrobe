from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, TryonRecord, Favorite
from ..schemas import TryonResponse, FavoriteCreate, FavoriteResponse, BaseResponse
from ..dependencies import get_current_user

router = APIRouter(prefix="/records", tags=["记录管理"])

# 试穿记录
@router.get("/history", response_model=List[TryonResponse])
def get_tryon_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取试穿历史记录"""
    offset = (page - 1) * page_size
    records = db.query(TryonRecord).filter(
        TryonRecord.owner_id == current_user.id
    ).order_by(TryonRecord.created_at.desc()).offset(offset).limit(page_size).all()
    
    return records

# 收藏管理
@router.post("/favorites", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
def add_favorite(
    favorite_data: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加收藏"""
    # 检查试穿记录是否存在
    tryon_record = db.query(TryonRecord).filter(
        TryonRecord.id == favorite_data.tryon_record_id,
        TryonRecord.owner_id == current_user.id
    ).first()
    
    if not tryon_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="试穿记录不存在"
        )
    
    # 检查是否已收藏
    existing = db.query(Favorite).filter(
        Favorite.owner_id == current_user.id,
        Favorite.tryon_record_id == favorite_data.tryon_record_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已收藏该试穿记录"
        )
    
    # 创建收藏
    favorite = Favorite(
        owner_id=current_user.id,
        tryon_record_id=favorite_data.tryon_record_id
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    
    # 关联试穿记录
    favorite.tryon_record = tryon_record
    
    return favorite

@router.get("/favorites", response_model=List[FavoriteResponse])
def get_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取收藏列表"""
    offset = (page - 1) * page_size
    favorites = db.query(Favorite).filter(
        Favorite.owner_id == current_user.id
    ).order_by(Favorite.created_at.desc()).offset(offset).limit(page_size).all()
    
    # 关联试穿记录
    for fav in favorites:
        fav.tryon_record = db.query(TryonRecord).filter(TryonRecord.id == fav.tryon_record_id).first()
    
    return favorites

@router.delete("/favorites/{favorite_id}", response_model=BaseResponse)
def delete_favorite(
    favorite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消收藏"""
    favorite = db.query(Favorite).filter(
        Favorite.id == favorite_id,
        Favorite.owner_id == current_user.id
    ).first()
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏记录不存在"
        )
    
    db.delete(favorite)
    db.commit()
    
    return BaseResponse(message="取消收藏成功")