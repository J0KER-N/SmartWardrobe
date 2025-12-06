from __future__ import annotations

from typing import Any, Dict

import httpx

from ..config import get_settings

settings = get_settings()


async def fetch_weather(city: str | None = None) -> Dict[str, Any]:
    if not settings.weather_api_url or not settings.weather_api_key:
        return {"temperature": 22, "humidity": 0.4, "conditions": "Clear"}

    params = {"q": city or "beijing", "appid": settings.weather_api_key, "units": "metric"}
    async with httpx.AsyncClient() as client:
        response = await client.get(str(settings.weather_api_url), params=params)
        response.raise_for_status()
        data = response.json()
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        return {
            "temperature": main.get("temp"),
            "humidity": main.get("humidity"),
            "conditions": weather.get("main"),
        }

