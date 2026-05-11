from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import Garment, RecommendationRecord, User
from ..schemas import GarmentResponse, RecommendationItem, RecommendationResponse
from .ai_clients import generate_recommendation_reason, summarize_outfit
from .image_storage import save_recommendation_preview
from .metrics import log_recommendation_show
from .outfit_logic import generate_outfit_recommendations
from .preference_learning import get_user_preference_profile, score_outfit_preference
from .weather import get_weather

logger = logging.getLogger(__name__)


@dataclass
class RecommendationPipelineResult:
    weather: Dict[str, Any]
    recommendations: List[RecommendationItem]
    garment_count: int


def _build_fallback_groups(garments: List[Garment]) -> List[Dict[str, Any]]:
    if not garments:
        return []

    selected = random.sample(garments, min(3, len(garments)))
    return [
        {
            "garment_ids": [g.id for g in selected],
            "garments": selected,
            "reason": "基于你的衣橱推荐的搭配",
        }
    ]


def run_recommendation_pipeline(
    db: Session,
    current_user: User,
    city: str,
    *,
    allow_weather_fallback: bool = True,
    allow_random_fallback: bool = True,
) -> RecommendationPipelineResult:
    """统一编排推荐流程：感知 -> 决策 -> 执行 -> 记录。"""
    weather = get_weather(city)
    if not weather:
        if not allow_weather_fallback:
            raise ValueError("获取天气信息失败")
        weather = {"temp_c": 20, "condition": "晴", "city": city}

    garments = db.query(Garment).filter(
        Garment.owner_id == current_user.id,
        Garment.is_deleted == False,
    ).all()

    if not garments:
        raise ValueError("暂无衣物，请先添加衣物到衣橱")

    preference_profile = get_user_preference_profile(current_user.id)
    outfit_groups = generate_outfit_recommendations(garments, weather, preference_profile)

    if not outfit_groups and allow_random_fallback:
        outfit_groups = _build_fallback_groups(garments)

    if allow_random_fallback and len(outfit_groups) < 3 and len(garments) >= 2:
        while len(outfit_groups) < 3:
            selected = random.sample(garments, min(3, len(garments)))
            outfit_groups.append(
                {
                    "garment_ids": [g.id for g in selected],
                    "garments": selected,
                    "reason": "基于你的衣橱推荐的搭配",
                }
            )

    outfit_groups = outfit_groups[:5]
    recommendations: List[RecommendationItem] = []

    for group in outfit_groups:
        garment_responses = [GarmentResponse.model_validate(garment) for garment in group["garments"]]
        description = summarize_outfit(garment_responses, weather)

        style = group.get("style")
        color = group.get("color")
        if not style or not color:
            reason_text = group.get("reason", "")
            if not style and "风格" in reason_text:
                for keyword in ["简约", "时尚", "休闲", "正式", "运动", "甜美", "复古"]:
                    if keyword in reason_text:
                        style = keyword
                        break
            if not color and "系" in reason_text:
                for keyword in ["深色", "浅色", "亮色", "暖色", "冷色"]:
                    if keyword in reason_text:
                        color = keyword
                        break

        reason = generate_recommendation_reason(garment_responses, weather, style, color)
        preview_image_url = save_recommendation_preview(
            [garment.image_url for garment in garment_responses],
            current_user.id,
        )

        preference_score = score_outfit_preference(garment_responses, preference_profile)
        confidence = min(0.95, round(0.45 + 0.08 * len(garment_responses) + 0.25 * preference_score, 2))

        item = RecommendationItem(
            garment_ids=group["garment_ids"],
            garments=garment_responses,
            description=description,
            reason=reason,
            confidence=confidence,
            preview_image_url=preview_image_url,
        )
        recommendations.append(item)

        record = RecommendationRecord(
            owner_id=current_user.id,
            garment_ids=item.garment_ids,
            garments=[g.model_dump(mode="json") for g in garment_responses],
            description=item.description,
            reason=item.reason,
            confidence=item.confidence,
        )
        db.add(record)

    db.commit()

    log_recommendation_show(
        current_user.id,
        {
            "city": city,
            "weather": weather,
            "recommendation_count": len(recommendations),
            "garment_count": len(garments),
            "confidence": [item.confidence for item in recommendations],
        },
    )

    return RecommendationPipelineResult(
        weather=weather,
        recommendations=recommendations,
        garment_count=len(garments),
    )