import os
import uuid
import logging
from datetime import datetime
from PIL import Image
from io import BytesIO
from fastapi import UploadFile, HTTPException

from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 初始化存储目录
def init_storage():
    """初始化图片存储目录"""
    if settings.object_storage_type == "local":
        os.makedirs(settings.image_storage_path, exist_ok=True)
        os.makedirs(os.path.join(settings.image_storage_path, "garments"), exist_ok=True)
        os.makedirs(os.path.join(settings.image_storage_path, "avatars"), exist_ok=True)
        os.makedirs(os.path.join(settings.image_storage_path, "tryon"), exist_ok=True)

# 调用初始化
init_storage()

# 图片校验
def validate_image(file: UploadFile, max_size: int = None) -> None:
    """校验图片格式和大小
    
    Args:
        file: 上传的文件
        max_size: 最大文件大小（字节），如果为None则使用默认的image_max_size
    """
    # 校验格式（支持更多格式）
    allowed_formats = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    # 如果content_type为空，尝试从文件名判断
    if not file.content_type:
        if file.filename:
            ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
            ext_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
            inferred_type = ext_map.get(ext)
            if inferred_type:
                logger.warning(f"文件 {file.filename} 缺少content_type，从扩展名推断为 {inferred_type}")
                return  # 允许通过
        raise HTTPException(status_code=400, detail=f"无法识别图片格式，仅支持{allowed_formats}格式图片")
    
    if file.content_type not in allowed_formats:
        raise HTTPException(status_code=400, detail=f"仅支持{allowed_formats}格式图片，当前格式: {file.content_type}")
    
    # 校验大小
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)  # 重置指针
    
    max_allowed = max_size if max_size is not None else settings.image_max_size
    logger.debug(f"文件大小检查: {file_size/1024/1024:.2f}MB vs 限制: {max_allowed/1024/1024:.2f}MB")
    if file_size > max_allowed:
        logger.warning(f"文件大小超过限制: {file_size/1024/1024:.2f}MB > {max_allowed/1024/1024:.2f}MB")
        raise HTTPException(status_code=400, detail=f"图片大小不能超过{max_allowed/1024/1024}MB")

def validate_tryon_image(file: UploadFile) -> None:
    """校验试衣用户照片格式和大小（使用更大的限制，符合Leffa标准）"""
    logger.info(f"验证试衣用户照片，限制大小: {settings.tryon_image_max_size/1024/1024}MB")
    validate_image(file, max_size=settings.tryon_image_max_size)

# 图片压缩
def compress_image(image: Image, quality: int = 85) -> Image:
    """压缩图片"""
    # 保持比例，最大宽度/高度限制为1920
    max_size = (1920, 1920)
    image.thumbnail(max_size)
    
    # 压缩质量
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    
    return image

# 本地存储核心函数
def _save_local(file: UploadFile, user_id: int, sub_dir: str) -> str:
    """本地存储图片"""
    # 生成唯一文件名
    # 从文件名或content_type获取扩展名
    if file.filename:
        file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else "jpg"
    else:
        # 从content_type推断扩展名
        content_type = file.content_type or "image/jpeg"
        ext_map = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}
        file_ext = ext_map.get(content_type, "jpg")
    
    file_name = f"{user_id}_{uuid.uuid4().hex}.{file_ext}"
    # 构建存储路径
    date_dir = datetime.now().strftime("%Y%m")
    save_dir = os.path.join(settings.image_storage_path, sub_dir, date_dir)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, file_name)
    
    try:
        # 确保文件指针在开头
        file.file.seek(0)
        # 读取并压缩图片
        image = Image.open(file.file)
        compressed_image = compress_image(image, settings.image_quality)
        # 保存图片
        compressed_image.save(save_path, quality=settings.image_quality)
        # 返回访问URL（本地路径转URL）
        return f"/uploads/{sub_dir}/{date_dir}/{file_name}"
    except Exception as e:
        logger.error(f"保存图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail="图片保存失败")

# 对象存储（示例，需根据实际S3/OSS扩展）
def _save_object_storage(file: UploadFile, user_id: int, sub_dir: str) -> str:
    """对象存储（S3/OSS），此处为示例框架"""
    raise NotImplementedError("对象存储功能需根据实际服务商实现")

# 对外暴露的保存函数
def save_image(file: UploadFile, user_id: int) -> str:
    """保存衣物图片"""
    validate_image(file)
    if settings.object_storage_type == "local":
        return _save_local(file, user_id, "garments")
    else:
        return _save_object_storage(file, user_id, "garments")

def save_avatar(file: UploadFile, user_id: int) -> str:
    """保存头像"""
    validate_image(file)
    if settings.object_storage_type == "local":
        return _save_local(file, user_id, "avatars")
    else:
        return _save_object_storage(file, user_id, "avatars")

def save_tryon_user_photo(file: UploadFile, user_id: int) -> str:
    """保存试衣用户照片（使用更大的大小限制）"""
    logger.info(f"保存试衣用户照片，文件大小限制: {settings.tryon_image_max_size/1024/1024}MB")
    validate_tryon_image(file)
    if settings.object_storage_type == "local":
        return _save_local(file, user_id, "garments")  # 试衣用户照片也保存在garments目录
    else:
        return _save_object_storage(file, user_id, "garments")

def save_tryon_image(image_data: bytes, user_id: int) -> str:
    """保存试穿图片"""
    # 模拟图片数据处理（实际需根据AI返回格式调整）
    file_name = f"{user_id}_{uuid.uuid4().hex}.jpg"
    date_dir = datetime.now().strftime("%Y%m")
    save_dir = os.path.join(settings.image_storage_path, "tryon", date_dir)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, file_name)
    
    try:
        image = Image.open(BytesIO(image_data))
        image.save(save_path)
        return f"/uploads/tryon/{date_dir}/{file_name}"
    except Exception as e:
        logger.error(f"保存试穿图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail="试穿图片保存失败")