from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List

import httpx
from tenacity import retry, retry_if_exception, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AIClientError(RuntimeError):
    """Base exception for AI client errors."""


class AIClientTimeoutError(AIClientError):
    """Raised when AI service request times out."""


class AIClientRateLimitError(AIClientError):
    """Raised when AI service rate limit is exceeded."""


class AIClientInvalidRequestError(AIClientError):
    """Raised when request parameters are invalid."""


async def _post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 60) -> dict:
    """Make POST request to AI service with error handling."""
    if not url:
        raise AIClientError("Endpoint is not configured")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as e:
        logger.error(f"AI service timeout: {url}, timeout={timeout}s")
        raise AIClientTimeoutError(f"Request to {url} timed out after {timeout}s") from e
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        if status_code == 429:
            logger.warning(f"AI service rate limit: {url}")
            raise AIClientRateLimitError(f"Rate limit exceeded for {url}") from e
        elif status_code in (400, 422):
            logger.error(f"AI service invalid request: {url}, {e.response.text}")
            raise AIClientInvalidRequestError(f"Invalid request to {url}: {e.response.text}") from e
        else:
            logger.error(f"AI service error: {url}, status={status_code}, {e.response.text}")
            raise AIClientError(f"Request failed with status {status_code}: {e.response.text}") from e
    except httpx.RequestError as e:
        logger.error(f"AI service connection error: {url}, {str(e)}")
        raise AIClientError(f"Connection error to {url}: {str(e)}") from e


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(
        lambda e: isinstance(e, (AIClientTimeoutError, AIClientRateLimitError))
    ),
)
async def extract_garment_tags(image_b64: str) -> dict[str, Any]:
    """Extract garment tags using FashionCLIP model."""
    if not settings.fashionclip_endpoint:
        logger.warning("FashionCLIP endpoint not configured")
        return {}

    if not image_b64 or len(image_b64) < 100:
        raise AIClientInvalidRequestError("Invalid image data provided")

    payload = {
        "image_base64": image_b64,
        "tasks": ["category", "scene", "style", "season", "colorway", "description"],
    }

    try:
        result = await _post_json(
            str(settings.fashionclip_endpoint),
            payload,
            timeout=settings.fashionclip_timeout,
        )
        tags = result.get("tags", {})
        logger.info(f"Extracted tags: {list(tags.keys())}")
        return tags
    except AIClientError as e:
        logger.error(f"Failed to extract garment tags: {str(e)}")
        raise


@retry(
    stop=stop_after_attempt(2),  # Fewer retries for long-running operations
    wait=wait_exponential(multiplier=2, min=5, max=30),
    retry=retry_if_exception_type(AIClientTimeoutError),
)
async def generate_tryon(user_image_b64: str, garment_images: List[str], prompt: str | None = None) -> str:
    """Generate try-on image using Leffa model."""
    if not settings.leffa_endpoint:
        raise AIClientError("Leffa endpoint is not configured")

    if not user_image_b64 or len(user_image_b64) < 100:
        raise AIClientInvalidRequestError("Invalid user image data")

    if not garment_images or len(garment_images) == 0:
        raise AIClientInvalidRequestError("At least one garment image is required")

    payload: Dict[str, Any] = {
        "user_image": user_image_b64,
        "garments": garment_images,
        "prompt": prompt or "Generate natural virtual try-on preview",
    }

    try:
        logger.info(f"Generating try-on with {len(garment_images)} garments")
        result = await _post_json(
            str(settings.leffa_endpoint),
            payload,
            timeout=settings.leffa_timeout,
        )

        result_b64 = result.get("result_image_base64")
        if not result_b64:
            raise AIClientError("No result image returned from Leffa service")

        logger.info("Try-on generation completed successfully")
        return result_b64
    except AIClientError as e:
        logger.error(f"Failed to generate try-on: {str(e)}")
        raise


async def summarize_outfit(weather: dict, garments: list[dict], rationale: str) -> str:
    """Generate outfit summary using Baichuan model."""
    if not settings.baichuan_api_url or not settings.baichuan_api_key:
        logger.debug("Baichuan API not configured, returning original rationale")
        return rationale

    headers = {"Authorization": f"Bearer {settings.baichuan_api_key}"}
    payload = {
        "model": settings.baichuan_model,
        "messages": [
            {"role": "system", "content": "你是一个智能衣橱搭配助手，擅长根据天气和衣物特点给出专业的穿搭建议。"},
            {
                "role": "user",
                "content": f"天气情况：{weather}。衣物信息：{garments}。选择理由：{rationale}。请用简洁的中文总结这套穿搭的推荐理由。",
            },
        ],
    }

    try:
        result = await _post_json(
            str(settings.baichuan_api_url),
            payload,
            headers=headers,
            timeout=settings.baichuan_timeout,
        )
        # Handle different response formats
        content = None
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0].get("message", {}).get("content")
        elif "content" in result:
            content = result["content"]
        elif "text" in result:
            content = result["text"]

        if content:
            logger.info("Outfit summary generated successfully")
            return content
        else:
            logger.warning("Unexpected response format from Baichuan API")
            return rationale
    except AIClientError as e:
        logger.warning(f"Failed to generate outfit summary, using fallback: {str(e)}")
        return rationale


def to_base64(binary: bytes) -> str:
    return base64.b64encode(binary).decode("utf-8")

