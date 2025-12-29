from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import re

# ------------------------------ 基础模型 ------------------------------
class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"

    class Config:
        from_attributes = True

# ------------------------------ 用户/认证模型 ------------------------------
class UserCreate(BaseModel):
    """用户注册请求"""
    phone: str
    password: str
    nickname: str = Field(default="用户")

    @validator("phone")
    def validate_phone(cls, v):
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式错误（需为11位有效手机号）")
        return v

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8 or not re.search(r"[a-zA-Z]", v) or not re.search(r"\d", v):
            raise ValueError("密码需至少8位，包含字母和数字")
        return v

class UserLogin(BaseModel):
    """用户登录请求"""
    phone: str
    password: str

class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    phone: str
    nickname: str
    avatar_url: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}

# ------------------------------ 衣物模型 ------------------------------
class GarmentCreate(BaseModel):
    """添加衣物请求"""
    name: str
    category: str
    color: Optional[str]
    season: Optional[str]
    manual_tags: List[str] = Field(default=list)

class GarmentUpdate(BaseModel):
    """更新衣物请求"""
    name: Optional[str]
    category: Optional[str]
    color: Optional[str]
    season: Optional[str]
    manual_tags: Optional[List[str]]

class GarmentResponse(BaseModel):
    """衣物信息响应"""
    id: int
    owner_id: int
    name: str
    category: str
    color: Optional[str]
    image_url: str
    tags: List[str]
    season: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}

# ------------------------------ 试穿模型 ------------------------------
class TryonCreate(BaseModel):
    """生成试穿请求"""
    garment_id: int
    user_photo_url: str

class TryonResponse(BaseModel):
    """试穿记录响应"""
    id: int
    owner_id: int
    garment_id: int
    user_photo_url: str
    tryon_image_url: str
    tryon_status: str
    created_at: datetime

    model_config = {"from_attributes": True}

# ------------------------------ 收藏模型 ------------------------------
class FavoriteCreate(BaseModel):
    """添加收藏请求"""
    tryon_record_id: int

class FavoriteResponse(BaseModel):
    """收藏记录响应"""
    id: int
    owner_id: int
    tryon_record_id: int
    created_at: datetime
    tryon_record: TryonResponse

    model_config = {"from_attributes": True}

# ------------------------------ 穿搭推荐模型 ------------------------------
class RecommendationRequest(BaseModel):
    """穿搭推荐请求"""
    city: str

class RecommendationItem(BaseModel):
    """单条推荐项"""
    garment_ids: List[int]
    garments: List[GarmentResponse]
    description: str
    reason: str  # 推荐理由（如"适合当前天气"）

class RecommendationResponse(BaseModel):
    """穿搭推荐响应"""
    recommendations: List[RecommendationItem]
    weather: Dict[str, Any]  # 天气信息，键值类型可变

# ------------------------------ 个人中心模型 ------------------------------
class ProfileUpdate(BaseModel):
    """更新个人信息请求"""
    nickname: Optional[str]
    avatar_url: Optional[str]

class PasswordUpdate(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, v):
        if len(v) < 8 or not re.search(r"[a-zA-Z]", v) or not re.search(r"\d", v):
            raise ValueError("新密码需至少8位，包含字母和数字")
        return v