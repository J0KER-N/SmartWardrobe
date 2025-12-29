from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .database import Base

class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nickname = Column(String, default="用户")
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # 关联关系
    garments = relationship("Garment", back_populates="owner", cascade="all, delete-orphan")
    tryon_records = relationship("TryonRecord", back_populates="owner", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="owner", cascade="all, delete-orphan")

class Garment(Base):
    """衣物模型"""
    __tablename__ = "garments"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)  # 上衣/裤子/外套/鞋等
    color = Column(String, nullable=True)
    image_url = Column(String, nullable=False)
    tags = Column(JSON, default=list)  # 标签列表：["休闲", "红色", "夏季"]
    season = Column(String, nullable=True)  # 春/夏/秋/冬
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # 关联关系
    owner = relationship("User", back_populates="garments")
    tryon_records = relationship("TryonRecord", back_populates="garment")

class TryonRecord(Base):
    """虚拟试穿记录"""
    __tablename__ = "tryon_records"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    garment_id = Column(Integer, ForeignKey("garments.id"), nullable=False)
    user_photo_url = Column(String, nullable=False)
    tryon_image_url = Column(String, nullable=False)
    tryon_status = Column(String, default="success")  # success/failed
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    owner = relationship("User", back_populates="tryon_records")
    garment = relationship("Garment", back_populates="tryon_records")
    favorites = relationship("Favorite", back_populates="tryon_record", cascade="all, delete-orphan")

class Favorite(Base):
    """收藏记录"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tryon_record_id = Column(Integer, ForeignKey("tryon_records.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    owner = relationship("User", back_populates="favorites")
    tryon_record = relationship("TryonRecord", back_populates="favorites")