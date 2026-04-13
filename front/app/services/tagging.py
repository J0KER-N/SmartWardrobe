import logging
from fastapi import UploadFile

from ..services.ai_clients import extract_garment_tags

logger = logging.getLogger(__name__)

def auto_tag_garment(file: UploadFile) -> list:
    """自动识别衣物标签"""
    try:
        # 读取文件数据
        file_data = file.file.read()
        # 调用AI提取标签
        tags = extract_garment_tags(file_data)
        # 重置文件指针（避免后续读取失败）
        file.file.seek(0)
        return tags
    except Exception as e:
        logger.error(f"自动标签识别失败: {str(e)}")
        return []