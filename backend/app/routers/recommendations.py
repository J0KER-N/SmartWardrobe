from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..dependencies import get_current_user, get_db
from ..services import outfit_logic, weather, ai_clients

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/daily", response_model=schemas.OutfitSuggestion)
async def daily_recommendation(
    payload: schemas.RecommendationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    weather_data = await weather.fetch_weather(city=payload.city or current_user.location)
    garments = outfit_logic.pick_outfit(db, current_user.id, weather_data)
    rationale = "根据天气温度和衣物标签选择最适合的组合"
    summary = await ai_clients.summarize_outfit(
        weather=weather_data,
        garments=[{"id": g.id, "category": g.category, "style": g.style} for g in garments],
        rationale=rationale,
    )

    return schemas.OutfitSuggestion(
        garments=garments,
        reason=summary,
        weather=weather_data,
    )

