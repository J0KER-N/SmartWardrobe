import httpx
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel
import base64

from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 自定义异常
class AIClientError(Exception):
    """AI服务基础异常"""
    pass

class AIClientTimeoutError(AIClientError):
    """超时异常"""
    pass

class AIClientRateLimitError(AIClientError):
    """限流异常"""
    pass

class AIClientInvalidRequestError(AIClientError):
    """请求参数错误"""
    pass

# 通用请求工具
async def _async_post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
    timeout: int = 60
) -> Dict:
    """异步POST请求（用于高并发场景）"""
    if not url:
        raise AIClientError("AI服务地址未配置")
    
    headers = headers or {}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise AIClientTimeoutError(f"请求超时（{timeout}秒）")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise AIClientRateLimitError("请求频率超限")
        elif e.response.status_code == 400:
            raise AIClientInvalidRequestError(f"请求参数错误: {e.response.text}")
        else:
            raise AIClientError(f"服务错误: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        raise AIClientError(f"连接失败: {str(e)}")

def _sync_post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
    timeout: int = 60
) -> Dict:
    """同步POST请求（兼容同步代码）"""
    if not url:
        raise AIClientError("AI服务地址未配置")
    
    headers = headers or {}
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise AIClientTimeoutError(f"请求超时（{timeout}秒）")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise AIClientRateLimitError("请求频率超限")
        elif e.response.status_code == 400:
            raise AIClientInvalidRequestError(f"请求参数错误: {e.response.text}")
        else:
            raise AIClientError(f"服务错误: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        raise AIClientError(f"连接失败: {str(e)}")

# ------------------------------ 虚拟试穿（Leffa） ------------------------------
def generate_tryon(user_photo_url: str, garment_image_url: str) -> Dict:
    """生成虚拟试穿图片"""
    if not settings.leffa_endpoint:
        raise AIClientError("Leffa服务地址未配置")
    
    payload = {
        "user_photo": user_photo_url,
        "garment_image": garment_image_url,
        "style": "natural",
        "resolution": "1080p"
    }
    
    logger.info(f"调用Leffa试穿服务 | 用户图片: {user_photo_url} | 衣物图片: {garment_image_url}")
    try:
        return _sync_post_json(
            url=settings.leffa_endpoint,
            payload=payload,
            timeout=120  # 试穿生成耗时较长
        )
    except AIClientError as e:
        logger.error(f"Leffa服务调用失败: {str(e)}")
        raise

# ------------------------------ 衣物标签识别（FashionCLIP） ------------------------------
def extract_garment_tags(image_data: bytes) -> List[str]:
    """提取衣物标签"""
    if not settings.fashionclip_endpoint:
        logger.warning("FashionCLIP未配置，返回默认标签")
        return ["未识别标签"]
    
    payload = {
        # 使用 Base64 编码以避免 hex 导致体积膨胀
        "image_data": base64.b64encode(image_data).decode(),
        "top_k": 5  # 返回前5个标签
    }
    
    logger.info("调用FashionCLIP标签识别服务")
    try:
        result = _sync_post_json(
            url=settings.fashionclip_endpoint,
            payload=payload,
            timeout=60
        )
        return result.get("tags", [])
    except AIClientError as e:
        logger.error(f"FashionCLIP调用失败: {str(e)}")
        return ["标签识别失败"]

# ------------------------------ 穿搭文案生成（百川） ------------------------------
def summarize_outfit(garments: List[Dict], weather: Dict) -> str:
    """生成穿搭描述文案"""
    if not settings.baichuan_api_key:
        logger.warning("百川API未配置，返回默认文案")
        return "今日穿搭推荐：适合当前天气的舒适搭配"
    
    # 构建提示词
    def _get_field(item, field, default=None):
        # 支持 dict-like、对象属性（SQLAlchemy 或 Pydantic 模型）
        try:
            # 属性访问优先（适用于 Pydantic / ORM 实例）
            if hasattr(item, field):
                return getattr(item, field)
        except Exception:
            pass
        try:
            # 字典访问回退
            return item.get(field, default) if isinstance(item, dict) else default
        except Exception:
            return default

    garment_desc = "\n".join([
        f"- {_get_field(g, 'category', '')}: {_get_field(g, 'name', '')}（{','.join(_get_field(g, 'tags', []) or [])}）"
        for g in garments
    ])
    prompt = f"""
    基于以下信息生成简洁优美的穿搭描述（50字以内）：
    天气：{weather['condition']}，温度{weather['temp_c']}℃
    衣物：{garment_desc}
    要求：口语化、友好，突出搭配亮点和适配天气的原因
    """
    
    payload = {
        "model": settings.baichuan_model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    headers = {
        "Authorization": f"Bearer {settings.baichuan_api_key}",
        "Content-Type": "application/json"
    }
    
    logger.info("调用百川大模型生成穿搭文案")
    try:
        result = _sync_post_json(
            url=settings.baichuan_endpoint,
            payload=payload,
            headers=headers,
            timeout=30
        )
        return result.get("choices", [{}])[0].get("message", {}).get("content", "今日穿搭推荐")
    except AIClientError as e:
        logger.error(f"百川模型调用失败: {str(e)}")
        return "今日穿搭推荐：适合当前天气的舒适搭配"