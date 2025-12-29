from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import User
from ..schemas import UserResponse, ProfileUpdate, PasswordUpdate, BaseResponse
from ..dependencies import get_current_user
from ..security import get_password_hash, verify_password
from ..services.image_storage import save_avatar

router = APIRouter(prefix="/profile", tags=["个人中心"])

@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user

@router.put("/me", response_model=UserResponse)
def update_profile(
    profile_data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新个人信息"""
    update_data = profile_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/avatar", response_model=UserResponse)
def update_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新头像"""
    try:
        avatar_url = save_avatar(file, current_user.id)
        current_user.avatar_url = avatar_url
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新头像失败: {str(e)}"
        )

@router.put("/password", response_model=BaseResponse)
def update_password(
    password_data: PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 更新新密码
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return BaseResponse(message="密码修改成功")