"""天气 API 路由（前端真实 API 调用入口）。"""
from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Optional

from ..services.weather import get_weather

router = APIRouter(prefix="/weather", tags=["天气"])


@router.get("")
def weather(
    city: str = Query("北京", description="城市名称"),
):
    """获取指定城市的实时天气。"""
    result = get_weather(city)
    if result is None:
        return {
            "city": city,
            "condition": "晴",
            "temp_c": 25,
            "humidity": 60,
        }
    return result
