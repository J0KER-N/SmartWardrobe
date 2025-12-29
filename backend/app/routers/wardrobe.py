from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import User, Garment
from ..schemas import GarmentCreate, GarmentUpdate, GarmentResponse, BaseResponse
from ..dependencies import get_current_user
from ..services.image_storage import save_image
from ..services.tagging import auto_tag_garment

router = APIRouter(prefix="/wardrobe", tags=["衣橱管理"])

@router.post("/items", response_model=GarmentResponse, status_code=status.HTTP_201_CREATED)
def create_garment(
    name: str = Form(...),
    category: str = Form(...),
    color: Optional[str] = Form(None),
    season: Optional[str] = Form(None),
    manual_tags: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加新衣物（支持 multipart/form-data）"""
    try:
        # 解析手动标签（前端可传逗号分隔字符串）
        manual_tags_list = [t.strip() for t in manual_tags.split(',')] if manual_tags else []

        # 自动生成标签（auto_tag_garment 会重置 file 指针）
        auto_tags = auto_tag_garment(file)

        # 保存图片
        image_url = save_image(file, current_user.id)

        # 合并标签
        all_tags = auto_tags + manual_tags_list

        # 创建衣物记录
        garment = Garment(
            owner_id=current_user.id,
            name=name,
            category=category,
            color=color,
            season=season,
            image_url=image_url,
            tags=all_tags
        )
        db.add(garment)
        db.commit()
        db.refresh(garment)

        return garment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加衣物失败: {str(e)}"
        )

@router.get("/items", response_model=List[GarmentResponse])
def get_garments(
    category: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取衣物列表（支持筛选和分页）"""
    # 构建查询条件
    query = db.query(Garment).filter(
        Garment.owner_id == current_user.id,
        Garment.is_deleted == False
    )
    
    # 筛选条件
    if category:
        query = query.filter(Garment.category == category)
    if color:
        query = query.filter(Garment.color == color)
    if season:
        query = query.filter(Garment.season == season)
    if tag:
        query = query.filter(Garment.tags.contains([tag]))
    
    # 分页
    offset = (page - 1) * page_size
    garments = query.offset(offset).limit(page_size).all()
    
    return garments

@router.get("/items/{garment_id}", response_model=GarmentResponse)
def get_garment(
    garment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单条衣物信息"""
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
    
    return garment

@router.put("/items/{garment_id}", response_model=GarmentResponse)
def update_garment(
    garment_id: int,
    garment_data: GarmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新衣物信息"""
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
    
    # 更新字段
    update_data = garment_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(garment, key, value)
    
    db.commit()
    db.refresh(garment)
    
    return garment

@router.delete("/items/{garment_id}", response_model=BaseResponse)
def delete_garment(
    garment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除衣物（软删除）"""
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
    
    garment.is_deleted = True
    db.commit()
    
    return BaseResponse(message="删除成功")