"""AI Provider 公共模块。

包含共享的异步 HTTP 工具函数、异常定义和媒体数据模型。
"""
from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List, Optional
from io import BytesIO

import httpx
from PIL import Image

logger = logging.getLogger(__name__)


# ─── 异常定义 ────────────────────────────────────────────────────────────

class AIClientError(Exception):
    """AI 服务基础异常。"""
    pass


class AIClientTimeoutError(AIClientError):
    """超时异常。"""
    pass


class AIClientRateLimitError(AIClientError):
    """限流异常。"""
    pass


class AIClientInvalidRequestError(AIClientError):
    """请求参数错误。"""
    pass


# ─── 数据类型 ────────────────────────────────────────────────────────────


def _find_media_url(data: Any) -> Optional[str]:
    """递归搜索嵌套 JSON 中的媒体 URL。"""
    if isinstance(data, dict):
        for key in ("video_url", "image_url", "output_url", "result_url",
                     "output_video_url", "result_video_url"):
            value = data.get(key)
            if value and isinstance(value, str) and value.startswith("http"):
                return value
            if isinstance(value, dict):
                nested = value.get("url")
                if isinstance(nested, str) and nested.startswith("http"):
                    return nested
        for v in data.values():
            found = _find_media_url(v)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_media_url(item)
            if found:
                return found
    return None



def _find_openai_image_data(data: Any) -> Optional[List[dict]]:
    """递归搜索 OpenAI 风格的 data: [{url|b64_json}, ...] 结构。"""
    if isinstance(data, dict):
        items = data.get("data")
        if isinstance(items, list) and items and all(isinstance(x, dict) for x in items):
            if any("url" in x or "b64_json" in x for x in items):
                return items
        for v in data.values():
            found = _find_openai_image_data(v)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_openai_image_data(item)
            if found:
                return found
    return None


# ─── 异步 HTTP 工具 ─────────────────────────────────────────────────────

async def async_post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
    timeout: int = 60,
    max_retries: int = 3,
    use_proxy: bool = False,
) -> Dict[str, Any]:
    """异步 POST 请求，带重试和异常处理。

    这是全库唯一的 HTTP POST 入口。
    同步版 _sync_post_json 已废弃，所有调用方应迁移至此函数。
    """
    if not url:
        raise AIClientError("AI 服务地址未配置")

    headers = headers or {}
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            retry_timeout = timeout * (attempt + 1) if attempt > 0 else timeout

            transport = httpx.AsyncHTTPTransport(
                retries=0,
                trust_env=use_proxy,
            )

            async with httpx.AsyncClient(timeout=retry_timeout, transport=transport) as client:
                logger.debug("POST %s (attempt %d/%d, timeout=%ds)", url, attempt + 1, max_retries, retry_timeout)
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    return response.json()
                elif "image" in content_type:
                    return {"image_data": response.content}
                else:
                    try:
                        return response.json()
                    except Exception:
                        logger.warning("无法解析为 JSON: %s", content_type)
                        return {"raw": response.text[:1000]}

        except httpx.TimeoutException:
            last_error = AIClientTimeoutError(f"请求超时 ({retry_timeout}s)")
            if attempt < max_retries - 1:
                logger.warning("请求超时，重试中 (attempt %d/%d)", attempt + 1, max_retries)
                continue
            raise last_error

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                raise AIClientRateLimitError("请求频率超限")
            elif status == 400:
                raise AIClientInvalidRequestError(f"请求参数错误: {e.response.text[:300]}")
            elif status == 503:
                if attempt < max_retries - 1:
                    logger.warning("服务暂不可用 (503)，重试中")
                    continue
                raise AIClientError(f"模型加载超时: {e.response.text[:300]}")
            else:
                raise AIClientError(f"服务错误 {status}: {e.response.text[:500]}")

        except httpx.RequestError as e:
            last_error = AIClientError(f"连接失败: {e}")
            if attempt < max_retries - 1:
                logger.warning("连接失败，重试中")
                continue
            raise last_error

    if last_error:
        raise last_error
    raise AIClientError("请求失败（未知错误）")


# ─── 图片工具 ────────────────────────────────────────────────────────────

def openai_style_image_to_bytes(
    data_list: List[dict],
) -> Optional[bytes]:
    """从 OpenAI 风格的 data 列表中提取第一张图片的字节。"""
    if not data_list:
        return None
    first = data_list[0]
    b64 = first.get("b64_json")
    if b64 and isinstance(b64, str):
        return base64.b64decode(b64)
    url = first.get("url")
    if url and isinstance(url, str) and url.startswith("http"):
        import httpx as sync_httpx
        r = sync_httpx.get(url, timeout=120)
        r.raise_for_status()
        return r.content
    return None


def extract_image_from_response(body: Dict) -> Optional[bytes]:
    """从 API 响应中提取图片数据，处理多种返回格式。"""
    # 1. OpenAI 风格的 data 数组
    img = openai_style_image_to_bytes(body.get("data") or [])
    if img:
        return img

    # 2. 递归搜索嵌套的 data 数组
    nested = _find_openai_image_data(body)
    if nested:
        img = openai_style_image_to_bytes(nested)
        if img:
            return img

    # 3. 递归搜索媒体 URL 并下载
    media_url = _find_media_url(body)
    if media_url:
        import httpx as sync_httpx
        r = sync_httpx.get(media_url, timeout=120)
        r.raise_for_status()
        return r.content

    return None


def detect_media_extension(data: bytes) -> str:
    """根据魔数判断媒体类型。"""
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"GIF8"):
        return "gif"
    if data[4:8] == b"ftyp" or b"ftyp" in data[:32]:
        return "mp4"
    return "jpg"
