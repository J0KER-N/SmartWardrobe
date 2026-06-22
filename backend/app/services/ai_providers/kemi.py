"""Kemi（可美网关）AI 服务提供者。

功能：
1. 虚拟试穿图片生成（同步 + 异步轮询）
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from .base import (
    AIClientError,
    AIClientTimeoutError,
    AIClientRateLimitError,
    extract_image_from_response,
)
from ...config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── 公共 API ────────────────────────────────────────────────────────────

async def generate_tryon(
    user_photo_url: str,
    garment_image_url: str,
) -> Dict[str, Any]:
    """生成虚拟试穿结果。

    支持两种模式：
    1. 同步：直接 POST 返回图片
    2. 异步轮询：POST 返回 task_id，通过轮询获取图片

    返回: {"image_data": bytes} 或 {"video_data": bytes, "video_url": str}
    """
    if not settings.kemi_gateway_api_key:
        raise AIClientError("KEMI_GATEWAY_API_KEY 未配置")

    # 准备参考图片 URL
    ref_urls = await _prepare_reference_urls(user_photo_url, garment_image_url)
    is_video = _is_video_config()

    # 构建请求
    payload = _build_tryon_payload(ref_urls, is_video)
    headers = _auth_headers()
    image_path = settings.kemi_tryon_images_path

    logger.info("KM 试衣请求: model=%s, video=%s", settings.kemi_tryon_image_model, is_video)

    # 首次 POST
    try:
        body = await async_post_tryon(headers, payload, image_path)
    except Exception as e:
        raise AIClientError(f"KM 试衣请求失败: {e}")

    if not body:
        raise AIClientError("KM 响应为空")

    # 尝试同步返回（图片直接返回）
    img = extract_image_from_response(body)
    if img:
        return _result_with_media(img)

    # 异步任务：提取 task_id 并轮询
    task_id = _extract_task_id(body)
    if not task_id:
        # 最后尝试从完整 body 中提取图片
        img = _bytes_from_full_response(body)
        if img:
            return _result_with_media(img)
        raise AIClientError(f"无法获取 task_id，响应: {str(body)[:500]}")

    logger.info("KM 异步任务: task_id=%s", task_id)

    # 异步轮询
    img_data = await _poll_task(task_id, headers, image_path, is_video)
    if img_data:
        return _result_with_media(img_data)

    raise AIClientTimeoutError(f"KM 轮询超时 (task_id={task_id})")


# ─── 内部实现 ────────────────────────────────────────────────────────────

async def _prepare_reference_urls(
    user_url: str,
    garment_url: str,
) -> List[str]:
    """将本地 URL 转换为可公开访问的 URL（必要时转为 data URI）。"""
    base_api = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

    def resolve(url: str) -> str:
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return f"{base_api}{url}"
        return f"{base_api}/{url}"

    resolved = [resolve(user_url), resolve(garment_url)]
    result: List[str] = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        for url in resolved:
            if _is_private_url(url):
                logger.info("内网地址 %s，转为 data URI", url)
                try:
                    r = await client.get(url, timeout=90.0)
                    r.raise_for_status()
                    ctype = (r.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
                    if ctype not in ("image/png", "image/jpeg", "image/webp"):
                        ctype = "image/jpeg"
                    b64 = base64.b64encode(r.content).decode("ascii")
                    result.append(f"data:{ctype};base64,{b64}")
                except Exception as e:
                    logger.warning("下载图片失败 %s: %s", url, e)
                    result.append(url)
            else:
                result.append(url)

    return result


def _is_private_url(url: str) -> bool:
    u = url.lower()
    if u.startswith("data:"):
        return False
    return any(x in u for x in ["127.0.0.1", "localhost", "192.168.", "10."])


def _is_video_config() -> bool:
    model = (settings.kemi_tryon_image_model or "").lower()
    path = (settings.kemi_tryon_images_path or "").lower()
    return (
        "seedance" in model
        or "doubao-seedance" in model
        or "/video/" in path
        or "/contents/generations/tasks" in path
    )


def _auth_headers() -> Dict[str, str]:
    key = (settings.kemi_gateway_api_key or "").strip()
    return {
        "Authorization": f"Bearer {key}",
        "X-Goog-Api-Key": key,
    }


def _build_tryon_payload(ref_urls: List[str], is_video: bool) -> Dict:
    prompt = settings.kemi_tryon_prompt
    if not is_video:
        return {
            "model": settings.kemi_tryon_image_model,
            "prompt": prompt,
            "image_url": ref_urls[0],
            "reference_image_url": ref_urls[1] if len(ref_urls) > 1 else None,
            "n": settings.kemi_tryon_n,
            "response_format": "b64_json",
        }

    # 视频模式
    return {
        "model": settings.kemi_tryon_image_model,
        "prompt": prompt,
        "image_url": ref_urls[0],
        "reference_image_urls": ref_urls[1:] if len(ref_urls) > 1 else [],
        "duration": settings.kemi_tryon_duration,
        "resolution": "720p",
    }


async def async_post_tryon(
    headers: Dict[str, str],
    payload: Dict,
    image_path: str,
) -> Dict[str, Any]:
    """发送试衣请求。"""
    base = settings.kemi_gateway_base_url
    url = f"{base.rstrip('/')}{image_path}"

    params = {"key": settings.kemi_gateway_api_key} if settings.kemi_gateway_api_key else {}

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, json=payload, headers=headers, params=params)
        r.raise_for_status()
        return r.json()


def _extract_task_id(body: Dict) -> Optional[str]:
    for key in ("task_id", "taskId", "id"):
        val = body.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    data = body.get("data")
    if isinstance(data, dict):
        for key in ("task_id", "taskId", "id"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


async def _poll_task(
    task_id: str,
    headers: Dict[str, str],
    image_path: str,
    is_video: bool,
) -> Optional[bytes]:
    """异步轮询任务结果。"""
    base = settings.kemi_gateway_base_url
    deadline = asyncio.get_event_loop().time() + settings.kemi_tryon_poll_timeout_sec
    interval = max(0.5, settings.kemi_tryon_poll_interval_sec)

    # 构建候选查询 URL
    candidates = [
        f"{base}/api/v3/contents/generations/tasks/{task_id}",
        f"{base}/api/v3/images/generations/{task_id}",
        f"{base}/v1/images/{image_path.split('/')[-1]}/{task_id}",
        f"{base}/v1/tasks/{task_id}",
    ]

    params = {}
    if settings.kemi_gateway_api_key:
        params["key"] = settings.kemi_gateway_api_key

    async with httpx.AsyncClient(timeout=90.0) as client:
        while asyncio.get_event_loop().time() < deadline:
            for url in candidates:
                try:
                    r = await client.get(url, params=params, headers=headers)
                    if r.status_code == 404:
                        continue
                    r.raise_for_status()
                    body = r.json()
                    if not isinstance(body, dict):
                        continue

                    # 检查是否有图片数据
                    img = extract_image_from_response(body)
                    if img:
                        return img

                    # 检查任务状态
                    status = str(body.get("status") or body.get("state") or body.get("task_status") or "").lower()
                    if status in ("failed", "error", "cancelled", "canceled"):
                        raise AIClientError(f"KM 任务失败: {str(body)[:500]}")
                    if status in ("succeeded", "success", "completed", "finished", "done"):
                        # 状态成功但无图片，等一小会儿再试
                        await asyncio.sleep(min(interval, 1.5))
                        continue

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        raise AIClientError("KM API Key 无效（401）")
                    continue
                except Exception:
                    continue

            await asyncio.sleep(interval)

    return None


def _result_with_media(data: bytes) -> Dict[str, Any]:
    ext = data[:4]
    if ext[4:8] == b"ftyp" or b"ftyp" in data[:32]:
        return {"video_data": data}
    return {"image_data": data}


def _bytes_from_full_response(body: Dict) -> Optional[bytes]:
    """从各种嵌套路径中提取图片字节。"""
    img = extract_image_from_response(body)
    if img:
        return img
    for key in ("image_url", "output_url", "video_url", "result_url", "output_video_url", "result_video_url"):
        v = body.get(key)
        if isinstance(v, str) and v.startswith("http"):
            try:
                import httpx as sync_httpx
                r = sync_httpx.get(v, timeout=120)
                r.raise_for_status()
                return r.content
            except Exception:
                continue
    return None
