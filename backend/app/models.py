from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship

from .database import Base

from enum import Enum as PyEnum


class TryOnStatus(str, PyEnum):
    pending = "pending"
    completed = "completed"
    failed = "failed"

class User(Base):
    """鐢ㄦ埛妯″瀷"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nickname = Column(String, default="鐢ㄦ埛")
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # 鍏宠仈鍏崇郴
    garments = relationship("Garment", back_populates="owner", cascade="all, delete-orphan")
    tryon_records = relationship("TryonRecord", back_populates="owner", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="owner", cascade="all, delete-orphan")

class Garment(Base):
    """琛ｇ墿妯″瀷"""
    __tablename__ = "garments"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)  # 涓婅。/瑁ゅ瓙/澶栧/闉嬬瓑
    color = Column(String, nullable=True)
    image_url = Column(String, nullable=False)
    tags = Column(JSON, default=list)  # 鏍囩鍒楄〃锛歔"浼戦棽", "绾㈣壊", "澶忓"]
    season = Column(String, nullable=True)  # 鏄?澶?绉?鍐?
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # 鍏宠仈鍏崇郴
    owner = relationship("User", back_populates="garments")
    tryon_records = relationship("TryonRecord", back_populates="garment")

class TryonRecord(Base):
    """铏氭嫙璇曠┛璁板綍"""
    __tablename__ = "tryon_records"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    garment_id = Column(Integer, ForeignKey("garments.id"), nullable=False)
    user_photo_url = Column(String, nullable=False)
    tryon_image_url = Column(String, nullable=False)
    tryon_status = Column(String, default="success")  # success/failed
    created_at = Column(DateTime, default=datetime.utcnow)

    # 鍏宠仈鍏崇郴
    owner = relationship("User", back_populates="tryon_records")
    garment = relationship("Garment", back_populates="tryon_records")
    favorites = relationship("Favorite", back_populates="tryon_record", cascade="all, delete-orphan")


# 鏃т唬鐮佷腑鍙兘浣跨敤浜嗕笉鍚屽ぇ灏忓啓鐨勭被鍚嶏紝鎻愪緵鍒悕浠ラ伩鍏?ImportError
TryOnRecord = TryonRecord

class Favorite(Base):
    """鏀惰棌璁板綍"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tryon_record_id = Column(Integer, ForeignKey("tryon_records.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 鍏宠仈鍏崇郴
    owner = relationship("User", back_populates="favorites")
    tryon_record = relationship("TryonRecord", back_populates="favorites")


class RecommendationRecord(Base):
    """绌挎惌鎺ㄨ崘璁板綍"""
    __tablename__ = "recommendation_records"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    garment_ids = Column(JSON, default=list)  # 鎺ㄨ崘娑夊強鐨勮。鐗㊣D鍒楄〃
    garments = Column(JSON, default=list)     # 鎺ㄨ崘鏃剁殑琛ｇ墿璇︾粏淇℃伅蹇収
    description = Column(String, nullable=False)  # 绌挎惌鎻忚堪鏂囨
    reason = Column(String, nullable=False)       # 鎺ㄨ崘鐞嗙敱
    confidence = Column(Float, nullable=True)      # 鎺ㄨ崘缃俊搴︼紙0.0 - 1.0锛?
    created_at = Column(DateTime, default=datetime.utcnow)

    # 鍏宠仈鍏崇郴
    owner = relationship("User")


class Feedback(Base):
    """鐢ㄦ埛鍙嶉璁板綍"""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    outfit_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)  # like|dislike|skip|collect|purchase
    meta = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")


class UserPreference(Base):
    """用户偏好模型（替代 JSON 文件存储）。"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    style_weights = Column(JSON, default=dict)
    color_weights = Column(JSON, default=dict)
    category_weights = Column(JSON, default=dict)
    tag_weights = Column(JSON, default=dict)
    feedback_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User")
