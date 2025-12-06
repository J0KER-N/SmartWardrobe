from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    nickname = Column(String(64), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    location = Column(String(128), nullable=True)
    gender = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    garments = relationship("Garment", back_populates="owner", cascade="all, delete-orphan")
    tryon_records = relationship("TryOnRecord", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("FavoriteLook", back_populates="user", cascade="all, delete-orphan")


class Garment(Base):
    __tablename__ = "garments"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    category = Column(String(64), nullable=False)
    scene = Column(String(64), nullable=True)
    style = Column(String(64), nullable=True)
    season = Column(String(32), nullable=True)
    colorway = Column(String(32), nullable=True)
    price = Column(Integer, nullable=True)
    purchased_at = Column(DateTime, nullable=True)
    image_url = Column(String(255), nullable=True)
    embeddings = Column(JSON, nullable=True)
    extra_tags = Column(JSON, default=dict, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="garments")
    tags = relationship("GarmentTag", back_populates="garment", cascade="all, delete-orphan")


class GarmentTag(Base):
    __tablename__ = "garment_tags"

    id = Column(Integer, primary_key=True)
    garment_id = Column(Integer, ForeignKey("garments.id"), nullable=False)
    key = Column(String(50), nullable=False)
    value = Column(String(100), nullable=False)

    garment = relationship("Garment", back_populates="tags")

    __table_args__ = (UniqueConstraint("garment_id", "key", name="uq_garment_tag_key"),)


class TryOnStatus(str, PyEnum):
    """Try-on status enumeration."""
    pending = "pending"
    completed = "completed"
    failed = "failed"


class TryOnRecord(Base):
    __tablename__ = "try_on_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    garment_ids = Column(JSON, nullable=False)
    result_image_url = Column(String(255), nullable=True)
    prompt = Column(Text, nullable=True)
    status = Column(Enum(TryOnStatus, native_enum=False, length=20), default=TryOnStatus.pending, nullable=False)
    meta_data = Column(JSON, default=dict, nullable=False)  # Renamed from 'metadata' to avoid conflict with SQLAlchemy's reserved attribute
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="tryon_records")
    favorite = relationship("FavoriteLook", back_populates="record", uselist=False)


class FavoriteLook(Base):
    __tablename__ = "favorite_looks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    record_id = Column(Integer, ForeignKey("try_on_records.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="favorites")
    record = relationship("TryOnRecord", back_populates="favorite")

