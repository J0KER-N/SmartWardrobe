"""百川（Baichuan）AI 服务提供者。

功能：
1. 提取服装标签（结构化 JSON + 标签列表）
2. 生成穿搭描述文案
3. 生成推荐理由
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .base import (
    AIClientError,
    async_post_json,
)

from ...config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── 公共 API ────────────────────────────────────────────────────────────

async def extract_garment_tags(image_data: bytes) -> Dict[str, Any]:
    """使用百川大模型识别服装的结构化标签。

    返回格式:
    {
        "category": "上装", "style": "休闲",
        "material": "棉", "color_palette": ["白色", "灰色"],
        "confidence": 0.85,
        "reason": "这是一件白色棉质短袖T恤..."
    }
    """
    if not settings.baichuan_api_key:
        logger.warning("百川API未配置，返回默认标签")
        return _get_default_structured_tags()

    prompt = (
        "请分析这张服装图片，返回结构化JSON标签：\n"
        '{"category":"服装类别","style":"风格","material":"材质",'
        '"color_palette":["颜色1","颜色2"],"confidence":0.8,'
        '"reason":"简短描述"}\n'
        "只返回JSON，不要其他文字。"
    )

    payload = {
        "model": settings.baichuan_model,
        "messages": [
            {"role": "system", "content": "你是一个服装分析专家，返回严格 JSON。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 300,
    }

    headers = {
        "Authorization": f"Bearer {settings.baichuan_api_key}",
        "Content-Type": "application/json",
    }

    try:
        result = await async_post_json(
            url=settings.baichuan_endpoint,
            payload=payload,
            headers=headers,
            timeout=30,
            use_proxy=True,
        )
        content = _extract_content(result)
        if content:
            parsed = _parse_structured_tags(content)
            if parsed:
                logger.info("标签识别成功: %s", parsed)
                return parsed
    except Exception as e:
        logger.warning("百川标签识别失败: %s", e)

    return _get_default_structured_tags()


async def summarize_outfit(garments: List[Dict], weather: Dict) -> str:
    """生成穿搭描述文案。"""
    if not settings.baichuan_api_key:
        return _fallback_outfit_text(garments)

    garment_desc = "\n".join([
        f"- {_g(g, 'category', '')}: {_g(g, 'name', '')}（{','.join(_g(g, 'tags', []) or [])}）"
        for g in garments
    ])

    prompt = (
        f"天气：{weather.get('condition','晴')}，{weather.get('temp_c',20)}℃\n"
        f"衣物：{garment_desc}\n"
        "生成20字以内穿搭描述，口语化，突出搭配亮点和天气适配原因。"
    )

    payload = _build_payload(prompt, max_tokens=100)
    try:
        result = await async_post_json(
            url=settings.baichuan_endpoint,
            payload=payload,
            headers=_auth_headers(),
            timeout=30,
            use_proxy=True,
        )
        content = _extract_content(result)
        if content and content.strip():
            return content.strip()
    except Exception as e:
        logger.warning("生成穿搭描述失败: %s", e)

    return _fallback_outfit_text(garments)


async def generate_recommendation_reason(
    garments: List[Dict],
    weather: Dict,
    style: Optional[str] = None,
    color: Optional[str] = None,
) -> str:
    """生成推荐理由。"""
    if not settings.baichuan_api_key:
        return _fallback_reason(weather, style, color)

    garment_desc = "\n".join([
        f"- {_g(g, 'name', '')}（{_g(g, 'category', '')}）"
        for g in garments
    ])

    weather_info = f"{weather.get('condition','晴')}，{weather.get('temp_c',20)}℃"
    style_text = f"{style}风格" if style else ""
    color_text = f"{color}系" if color else ""

    prompt = (
        f"天气：{weather_info}\n"
        f"衣物：{garment_desc}\n"
        f"{style_text} {color_text}\n"
        "生成20字以内的推荐理由，解释这套搭配适合天气的原因。"
    )

    payload = _build_payload(prompt, max_tokens=80)
    try:
        result = await async_post_json(
            url=settings.baichuan_endpoint,
            payload=payload,
            headers=_auth_headers(),
            timeout=30,
            use_proxy=True,
        )
        content = _extract_content(result)
        if content and content.strip():
            return content.strip()
    except Exception as e:
        logger.warning("生成推荐理由失败: %s", e)

    return _fallback_reason(weather, style, color)


# ─── 内部工具 ────────────────────────────────────────────────────────────

def _auth_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.baichuan_api_key}",
        "Content-Type": "application/json",
    }


def _build_payload(user_prompt: str, max_tokens: int = 200) -> Dict:
    return {
        "model": settings.baichuan_model,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }


def _extract_content(result: Dict) -> str:
    for path in [("choices", 0, "message", "content"),
                 ("output", "choices", 0, "message", "content")]:
        try:
            val = result
            for key in path:
                val = val[key]
            return str(val)
        except (KeyError, IndexError, TypeError):
            continue
    return ""


def _g(item: Any, field: str, default: Any = None) -> Any:
    """安全地从 dict 或对象获取字段。"""
    if hasattr(item, field):
        try:
            return getattr(item, field)
        except Exception:
            pass
    if isinstance(item, dict):
        return item.get(field, default)
    return default


def _parse_structured_tags(content: str) -> Optional[Dict]:
    """解析 LLM 返回的 JSON 标签。"""
    # 尝试直接解析
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        else:
            return None

    required = ["category", "style", "material", "color_palette", "confidence", "reason"]
    if all(f in data for f in required):
        data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
        return data
    return None


def _get_default_structured_tags() -> Dict:
    return {
        "category": "未识别",
        "style": "未识别",
        "material": "未识别",
        "color_palette": ["未识别"],
        "confidence": 0.0,
        "reason": "无法识别标签，请重新上传清晰的衣物图片。",
    }


def _fallback_outfit_text(garments: List) -> str:
    names = [_g(g, "name", "") for g in garments if g]
    if names:
        return f"今日穿搭推荐：{'、'.join(names[:3])}的舒适搭配，适合当前天气。"
    return "今日穿搭推荐：适合当前天气的舒适搭配。"


def _fallback_reason(weather: Dict, style: Optional[str], color: Optional[str]) -> str:
    parts = []
    if style:
        parts.append(f"{style}风格")
    if color:
        parts.append(f"{color}系搭配")
    wi = f"{weather.get('condition','晴')}，{weather.get('temp_c',20)}℃"
    return f"{'，'.join(parts)}适合{wi}的天气" if parts else f"适合{wi}的天气"
