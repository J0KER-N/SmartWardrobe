import httpx
import logging
from typing import Dict, Optional

from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

def get_weather(city: str) -> Optional[Dict]:
    """获取城市天气信息"""
    # 当配置为默认占位符或未设置时，返回模拟数据以保证本地功能可用
    if not settings.weather_api_key or str(settings.weather_api_key).startswith("replace"):
        logger.warning("天气API密钥未配置或为占位符，返回模拟数据")
        return {
            "city": city,
            "condition": "晴",
            "temp_c": 25,
            "humidity": 60
        }
    
    # 构建请求参数
    params = {
        "key": settings.weather_api_key,
        "q": city,
        "aqi": "no"
    }
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(settings.weather_endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 解析天气数据
            current = data.get("current", {})
            location = data.get("location", {})
            
            return {
                "city": location.get("name", city),
                "condition": current.get("condition", {}).get("text", "未知"),
                "temp_c": current.get("temp_c", 20),
                "humidity": current.get("humidity", 60),
                "wind_kph": current.get("wind_kph", 0)
            }
    except Exception as e:
        logger.error(f"获取天气失败: {str(e)}")
        return None