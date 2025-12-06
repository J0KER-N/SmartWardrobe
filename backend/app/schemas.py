from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str | None = None


class UserBase(BaseModel):
    phone: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    gender: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    gender: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)


class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Tag(BaseModel):
    key: str
    value: str


class GarmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=64)
    scene: Optional[str] = None
    style: Optional[str] = None
    season: Optional[str] = None
    colorway: Optional[str] = None
    price: Optional[int] = None
    purchased_at: Optional[datetime] = None
    extra_tags: dict[str, Any] | None = None


class GarmentCreate(GarmentBase):
    pass


class GarmentUpdate(GarmentBase):
    is_deleted: Optional[bool] = None


class GarmentOut(GarmentBase):
    id: int
    image_url: Optional[str]
    tags: List[Tag] = []
    created_at: datetime

    class Config:
        from_attributes = True


class TryOnRequest(BaseModel):
    garment_ids: List[int] = Field(min_length=1)
    prompt: Optional[str] = None


class TryOnResponse(BaseModel):
    record_id: int
    status: str
    result_image_url: Optional[str] = None
    created_at: datetime


class RecommendationRequest(BaseModel):
    city: Optional[str] = None


class OutfitSuggestion(BaseModel):
    garments: List[GarmentOut]
    reason: str
    weather: dict[str, Any]


class FavoriteCreate(BaseModel):
    record_id: int
    notes: Optional[str] = None


class FavoriteOut(BaseModel):
    id: int
    record_id: int
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

