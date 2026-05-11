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
    reason: Optional[str] = None  # 标签识别理由
    created_at: datetime
    
    model_config = {"from_attributes": True}


# ------------------------------ 结构化标签模型 ------------------------------
class StructuredTag(BaseModel):
    """结构化标签信息"""
    category: str  # 衣物类别：上衣/裤子/外套/鞋等
    style: str  # 风格：休闲/正式/运动等
    material: str  # 材质：棉/聚酯/羊毛等
    color_palette: List[str]  # 颜色调色板：["白色", "浅灰色"]
    confidence: float = Field(ge=0, le=1)  # 识别置信度（0-1）
    reason: str  # 识别理由/解释
    
    model_config = {"from_attributes": True}


class AutoTagResponse(BaseModel):
    """自动标签识别响应"""
    success: bool = True
    message: str = "标签识别成功"
    tag_info: Optional[StructuredTag] = None  # 结构化标签信息
    raw_tags: List[str] = Field(default=list)  # 原始标签列表（向后兼容）
    
    model_config = {"from_attributes": True}


class FeedbackCreate(BaseModel):
    """创建反馈请求"""
    garment_id: Optional[int] = None
    tryon_record_id: Optional[int] = None
    feedback_type: str  # tag_accuracy/recommendation_quality/general
    feedback_text: str
    rating: Optional[int] = Field(None, ge=1, le=5)


class FeedbackResponse(BaseModel):
    """反馈信息响应"""
    id: int
    owner_id: int
    garment_id: Optional[int]
    tryon_record_id: Optional[int]
    feedback_type: str
    feedback_text: str
    rating: Optional[int]
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
    garment: Optional[GarmentResponse] = None  # 关联的衣物信息

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


class RecommendationRecordResponse(BaseModel):
    """穿搭推荐记录响应"""
    id: int
    owner_id: int
    garment_ids: List[int]
    garments: List[GarmentResponse]
    description: str
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}

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