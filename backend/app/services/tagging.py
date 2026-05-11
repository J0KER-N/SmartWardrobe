import logging
from typing import Dict, List, Any
from fastapi import UploadFile

from ..services.ai_clients import extract_garment_tags

logger = logging.getLogger(__name__)

def auto_tag_garment(file: UploadFile) -> Dict[str, Any]:
    """自动识别衣物标签，返回结构化标签信息
    
    返回格式：
    {
        "success": True,
        "message": "标签识别成功",
        "tag_info": {
            "category": "上衣",
            "style": "休闲",
            "material": "棉",
            "color_palette": ["白色", "灰色"],
            "confidence": 0.85,
            "reason": "这是一件白色棉质短袖T恤..."
        },
        "raw_tags": ["上衣", "短袖", "白色", "休闲", "棉"]  # 向后兼容
    }
    """
    try:
        # 读取文件数据
        file_data = file.file.read()
        
        # 调用AI提取结构化标签
        structured_tag = extract_garment_tags(file_data)
        
        # 重置文件指针（避免后续读取失败）
        file.file.seek(0)
        
        # 从结构化标签生成原始标签列表（向后兼容）
        raw_tags = _generate_raw_tags_from_structured(structured_tag)
        
        return {
            "success": True,
            "message": "标签识别成功",
            "tag_info": structured_tag,
            "raw_tags": raw_tags
        }
    except Exception as e:
        logger.error(f"自动标签识别失败: {str(e)}")
        return {
            "success": False,
            "message": f"标签识别失败: {str(e)}",
            "tag_info": None,
            "raw_tags": []
        }


def _generate_raw_tags_from_structured(structured_tag: Dict) -> List[str]:
    """从结构化标签生成原始标签列表（向后兼容）"""
    if not structured_tag:
        return []
    
    tags = []
    
    # 添加 category
    if structured_tag.get("category") and structured_tag["category"] != "未识别":
        tags.append(structured_tag["category"])
    
    # 添加 style
    if structured_tag.get("style") and structured_tag["style"] != "未识别":
        tags.append(structured_tag["style"])
    
    # 添加 material
    if structured_tag.get("material") and structured_tag["material"] != "未识别":
        tags.append(structured_tag["material"])
    
    # 添加 color_palette 中的颜色
    if structured_tag.get("color_palette"):
        for color in structured_tag["color_palette"]:
            if color and color != "未识别":
                tags.append(color)
    
    return tags