"""服装标签自动识别模块。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..services.ai_clients import extract_garment_tags

logger = logging.getLogger(__name__)


def auto_tag_garment(file) -> Dict[str, Any]:
    """自动识别服装标签，返回结构化标签信息。

    返回格式:
    {
        "success": True,
        "message": "标签识别成功",
        "tag_info": { ... },
        "raw_tags": ["上装", "短袖", ...]
    }

    当识别失败时返回空列表而非虚假数据。
    """
    try:
        file_data = file.file.read()
        structured_tag = extract_garment_tags(file_data)
        # 重置文件指针（上游可能继续读取）
        file.file.seek(0)

        # 过滤无效标签
        tag_info = structured_tag or {}
        is_valid = (
            tag_info.get("category") not in (None, "未识别")
            and tag_info.get("confidence", 0) > 0.1
        )

        if not is_valid:
            return {
                "success": False,
                "message": "无法识别服装标签，请稍后重试。",
                "tag_info": None,
                "raw_tags": [],
            }

        raw_tags = _generate_raw_tags(tag_info)
        return {
            "success": True,
            "message": "标签识别成功",
            "tag_info": tag_info,
            "raw_tags": raw_tags,
        }
    except Exception as e:
        logger.error("自动标签识别失败: %s", e)
        return {
            "success": False,
            "message": f"标签识别失败: {e}",
            "tag_info": None,
            "raw_tags": [],
        }


def _generate_raw_tags(structured: Dict) -> List[str]:
    """从结构化标签生成扁平标签列表。"""
    tags = []
    for field in ("category", "style", "material"):
        val = structured.get(field)
        if val and val != "未识别":
            tags.append(str(val))
    colors = structured.get("color_palette", [])
    for c in colors:
        if c and c != "未识别":
            tags.append(str(c))
    return tags
