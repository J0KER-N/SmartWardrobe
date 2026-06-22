"""AI 客户端 Facade —— 向后兼容的入口。

内部实现已拆分到 services/ai_providers/ 子包。
此文件仅做重导出和同步包装。
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .ai_providers.base import (
    AIClientError,
    AIClientTimeoutError,
    AIClientRateLimitError,
    AIClientInvalidRequestError,
)

from .ai_providers.kemi import generate_tryon as _async_generate_tryon
from .ai_providers.baichuan import (
    extract_garment_tags as _async_extract_garment_tags,
    summarize_outfit as _async_summarize_outfit,
    generate_recommendation_reason as _async_generate_recommendation_reason,
)


def generate_tryon(user_photo_url: str, garment_image_url: str) -> Dict[str, Any]:
    """同步包装：生成虚拟试穿图片。"""
    return _run_async(_async_generate_tryon(user_photo_url, garment_image_url))


def extract_garment_tags(image_data: bytes) -> Dict[str, Any]:
    """同步包装：提取服装结构化标签。"""
    return _run_async(_async_extract_garment_tags(image_data))


def summarize_outfit(garments: List[Dict], weather: Dict) -> str:
    """同步包装：生成穿搭描述文案。"""
    return _run_async(_async_summarize_outfit(garments, weather))


def generate_recommendation_reason(
    garments: List[Dict],
    weather: Dict,
    style: Optional[str] = None,
    color: Optional[str] = None,
) -> str:
    """同步包装：生成推荐理由。"""
    return _run_async(
        _async_generate_recommendation_reason(garments, weather, style, color)
    )


def _run_async(coro):
    """在已有事件循环中安全地运行协程。"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


__all__ = [
    "AIClientError",
    "AIClientTimeoutError",
    "AIClientRateLimitError",
    "AIClientInvalidRequestError",
    "generate_tryon",
    "extract_garment_tags",
    "summarize_outfit",
    "generate_recommendation_reason",
]
